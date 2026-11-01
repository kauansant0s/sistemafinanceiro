from decimal import Decimal
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.http import require_http_methods, require_POST
from .forms import BaixaForm, FiltroLancamentosForm, LancamentoEdicaoForm, LancamentoForm, _valor_br, normalizar
from .models import Caixa, ContaFinanceira, FormaBaixa, Lancamento, SubCentro
import json
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime

def _subcentros_do_centro(centro_id):
    if centro_id and str(centro_id).isdigit():
        return SubCentro.objects.filter(centro_id=centro_id)
    return SubCentro.objects.none()


@login_required
def novo_lancamento(request):
    if request.method == "POST":
        form = LancamentoForm(request.POST)
        if form.is_valid():
            lancamento = form.save(commit=False)
            lancamento.criado_por = request.user # Salva o usuário logado
            lancamento.save()
            
            messages.success(request, "Lançamento salvo com sucesso.")
            return redirect("financeiro:novo_lancamento")
        centro_id = request.POST.get("centro")
        subcentro_selecionado = request.POST.get("subcentro")
        conta_id = request.POST.get("conta", "")
    else:
        form = LancamentoForm()
        centro_id = subcentro_selecionado = None
        conta_id = ""

    conta_atual = None
    if conta_id.isdigit():
        conta_atual = ContaFinanceira.objects.filter(pk=conta_id).first()

    return render(request, "financeiro/novo_lancamento.html", {
        "form": form,
        "ano_atual": timezone.localdate().year,
        "subcentros": _subcentros_do_centro(centro_id),
        "subcentro_selecionado": subcentro_selecionado,
        "conta_atual": conta_atual,
    })


@login_required
def subcentros(request):
    """Devolve só as <option> do sub-centro (o HTMX troca dentro do select)."""
    template = (
        "partials/subcentro_filtro_options.html"
        if request.GET.get("filtro")
        else "partials/subcentro_options.html"
    )
    return render(request, template, {
        "subcentros": _subcentros_do_centro(request.GET.get("centro")),
        "subcentro_selecionado": None,
    })


@login_required
def buscar_contas(request):
    """Devolve a lista de contas que combinam com o que foi digitado."""
    q = normalizar(request.GET.get("q", "").strip())
    contas = []
    if q:
        contas = [
            c for c in ContaFinanceira.objects.filter(ativa=True)
            if q in normalizar(str(c))
        ][:10]
    return render(request, "partials/contas_resultados.html", {"contas": contas})

@login_required
@vary_on_headers("HX-Request")
def lancamentos(request):
    buscou = bool(request.GET)  # a lista só aparece depois que o usuário pesquisa
    form = FiltroLancamentosForm(request.GET or None)
    qs = Lancamento.objects.select_related("subcentro__centro", "conta")

    if buscou and form.is_valid():
        qs = form.filtrar(qs)
    else:
        qs = qs.none()

    # Os totais são da pesquisa inteira, mesmo com receitas/despesas ocultadas
    totais = qs.aggregate(
        receitas=Sum("valor", filter=Q(conta__tipo="R")),
        despesas=Sum("valor", filter=Q(conta__tipo="D")),
    )
    # O resumo só faz sentido quando o resultado tem receitas E despesas
    mostrar_resumo = totais["receitas"] is not None and totais["despesas"] is not None
    receitas = totais["receitas"] or Decimal("0")
    despesas = totais["despesas"] or Decimal("0")

    # Clicar em "Receitas" esconde as receitas (ocultar=R), e vice-versa
    ocultar = request.GET.get("ocultar", "")
    if ocultar not in ("R", "D") or not mostrar_resumo:
        ocultar = ""
    lista = qs.exclude(conta__tipo=ocultar) if ocultar else qs

    pagina = Paginator(lista, 50).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    def url_alternar(tipo):
        p = params.copy()
        if ocultar == tipo:
            p.pop("ocultar", None)
        else:
            p["ocultar"] = tipo
        return f"{reverse('financeiro:lancamentos')}?{p.urlencode()}"

    contexto = {
        "form": form,
        "buscou": buscou,
        "pagina": pagina,
        "querystring": params.urlencode(),
        "receitas": receitas,
        "despesas": despesas,
        "saldo": receitas - despesas,
        "ocultar": ocultar,
        "mostrar_resumo": mostrar_resumo,
        "url_alternar_receitas": url_alternar("R"),
        "url_alternar_despesas": url_alternar("D"),
    }

    # Só devolve o pedaço da tabela quando é o HTMX pedindo
    # (e não quando o navegador restaura o histórico, que precisa da página inteira).
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "partials/tabela_lancamentos.html", contexto)

    contexto["caixas"] = Caixa.objects.filter(ativo=True)
    contexto["formas_baixa"] = FormaBaixa.objects.filter(ativo=True)
    contexto["subcentros"] = _subcentros_do_centro(request.GET.get("centro"))
    contexto["subcentro_selecionado"] = request.GET.get("subcentro")
    return render(request, "financeiro/lancamentos.html", contexto)

@login_required
def importacoes(request):
    return render(request, "financeiro/importacoes.html")

# ---- Edição na própria linha da lista (HTMX) ----

def _lancamento_ou_404(pk):
    return get_object_or_404(Lancamento.objects.select_related("subcentro__centro", "conta"), pk=pk)


@login_required
def lancamento_linha(request, pk):
    """Mostra a linha normal (usado ao cancelar a edição)."""
    if not request.htmx:
        return redirect("financeiro:lancamentos")
    return render(request, "partials/_lancamento.html", {"l": _lancamento_ou_404(pk), "detalhe_aberto": True})


@login_required
@require_http_methods(["GET", "POST"])
def lancamento_editar(request, pk):
    """GET: linha em modo de edição. POST: salva; se algo estiver errado, volta a edição com os avisos."""
    if not request.htmx:
        return redirect("financeiro:lancamentos")
    l = _lancamento_ou_404(pk)

    if request.method == "POST":
        form = LancamentoEdicaoForm(request.POST, instance=l)
        if form.is_valid():
            form.save()
            l = _lancamento_ou_404(pk)
            return render(request, "partials/_lancamento.html", {"l": l, "detalhe_aberto": True, "salvo": True})
    else:
        form = LancamentoEdicaoForm(instance=l)

    conta_id = str(form["conta"].value() or "")
    conta_atual = ContaFinanceira.objects.filter(pk=conta_id).first() if conta_id.isdigit() else None
    return render(request, "partials/_lancamento_edicao.html", {
        "l": _lancamento_ou_404(pk),
        "form": form,
        "subcentros": _subcentros_do_centro(form["centro"].value()),
        "subcentro_selecionado": form["subcentro"].value(),
        "conta_atual": conta_atual,
    })

@login_required
@require_POST
def excluir_lancamentos(request):
    """Exclui os lançamentos marcados na lista. O histórico (simple-history) guarda quem excluiu."""
    ids = [i for i in request.POST.getlist("ids") if i.isdigit()]
    excluidos = []
    with transaction.atomic():
        # um a um, para o histórico registrar cada exclusão
        for l in Lancamento.objects.filter(pk__in=ids):  # baixados não se excluem
            excluidos.append(l.pk)
            l.delete()
    resposta = HttpResponse(status=204)
    resposta["HX-Trigger"] = json.dumps({"lancamentosExcluidos": {"qtd": len(excluidos), "ids": excluidos}})
    return resposta


@login_required
@require_POST
def desfazer_exclusao(request):
    """Recria, a partir do histórico, lançamentos que o próprio usuário acabou de excluir."""
    ids = [int(i) for i in request.POST.getlist("ids") if i.isdigit()]
    limite = timezone.now() - timedelta(minutes=2)  # só dá para desfazer o que acabou de acontecer
    qtd = 0
    with transaction.atomic():
        for pk in ids:
            if Lancamento.objects.filter(pk=pk).exists():
                continue
            registro = (
                Lancamento.history
                .filter(id=pk, history_type="-", history_user=request.user, history_date__gte=limite)
                .order_by("-history_date").first()
            )
            if registro is None:
                continue
            registro.instance.save()
            # o save() grava "criado em" com a hora de agora; devolve a data original
            Lancamento.objects.filter(pk=pk).update(criado_em=registro.criado_em)
            qtd += 1
    resposta = HttpResponse(status=204)
    resposta["HX-Trigger"] = json.dumps({"lancamentosRestaurados": {"qtd": qtd}})
    return resposta

# ---- Baixa de lançamentos ----

def _opcoes_com_novo(request, modelo, rotulo_novo, campo):
    """Cria o item digitado (ou reaproveita o que já existe com o mesmo nome) e devolve as <option> do select."""
    nome = " ".join(request.POST.get(campo, "").split())
    novo = None
    if nome:
        novo = modelo.objects.filter(nome__iexact=nome).first()
        if novo is None:
            novo = modelo.objects.create(nome=nome)
        elif not novo.ativo:
            novo.ativo = True
            novo.save(update_fields=["ativo"])
    return render(request, "partials/opcoes_select.html", {
        "objetos": modelo.objects.filter(ativo=True),
        "selecionado_id": novo.pk if novo else None,
        "rotulo_novo": rotulo_novo,
    })


@login_required
@require_POST
def criar_caixa(request):
    return _opcoes_com_novo(request, Caixa, "Criar novo caixa...", "novo_caixa")


@login_required
@require_POST
def criar_forma_baixa(request):
    return _opcoes_com_novo(request, FormaBaixa, "Criar nova forma de baixa...", "novo_forma")


@login_required
@require_POST
def baixar_lancamentos(request):
    """Baixa os lançamentos marcados. Suporta baixa parcial se for um único item."""
    form = BaixaForm(request.POST)
    ids = [int(i) for i in request.POST.getlist("ids") if i.isdigit()]
    lancamentos = list(Lancamento.objects.filter(pk__in=ids, data_baixa__isnull=True))
    erros = []

    if not lancamentos:
        erros.append("Nenhum lançamento para baixar (os já baixados são ignorados).")
    
    for campo_erros in form.errors.values():
        erros.extend(campo_erros)

    valores_baixados = {}
    
    # Se for apenas 1 lançamento, lê o valor digitado (pode ser parcial)
    if len(lancamentos) == 1:
        l = lancamentos[0]
        try:
            valor_pago = _valor_br(request.POST.get(f"valor_baixado_{l.pk}"))
        except ValidationError:
            valor_pago = None
        
        if valor_pago is None or valor_pago <= 0:
            erros.append(f"Informe um valor baixado válido para «{l.descricao}».")
        else:
            valores_baixados[l.pk] = valor_pago
            
    # Se for mais de 1, assume o valor total (bruto) para todos
    else:
        for l in lancamentos:
            valores_baixados[l.pk] = l.valor

    if erros:
        return render(request, "partials/baixa_erros.html", {"erros": erros})

    with transaction.atomic():
        for l in lancamentos:  # um a um, para o histórico registrar cada baixa
            l.data_baixa = form.cleaned_data["data_baixa"]
            l.caixa = form.cleaned_data["caixa"]
            l.forma_baixa = form.cleaned_data["forma_baixa"]
            l.valor_baixado = valores_baixados[l.pk]
            l.baixado_por = request.user
            l.save() # O save() do model vai calcular o liquido sozinho agora

    resposta = HttpResponse(status=204)
    resposta["HX-Trigger"] = json.dumps({"lancamentosBaixados": {"qtd": len(lancamentos)}})
    return resposta

@login_required
def lancamento_versoes(request, pk):
    """Retorna o histórico de versões do lançamento em JSON para o modal."""
    if not request.htmx:
        return redirect("financeiro:lancamentos")
    
    # Pega todo o histórico daquele lançamento, da mais nova para a mais velha
    historicos = Lancamento.history.filter(id=pk).order_by('-history_date')
    
    dados = []
    for h in historicos:
        # Pula a versão atual para mostrar só as antigas (opcional, mas fica mais limpo)
        if h.history_type == '+':
            acao = 'Criado'
        elif h.history_type == '~':
            acao = 'Editado'
        elif h.history_type == '-':
            acao = 'Excluído'
        
        dados.append({
            'data': timezone.localtime(h.history_date).strftime('%d/%m/%Y %H:%M'),
            'acao': acao,
            'usuario': h.history_user.nome_completo if h.history_user else 'Sistema',
            'descricao': h.descricao,
            'valor': float(h.valor),
            'liquidado': float(h.liquido) if h.liquido else None,
            'baixado_em': h.data_baixa.strftime('%d/%m/%Y') if h.data_baixa else None,
            'caixa': h.caixa.nome if h.caixa else None,
            'iso_date': h.history_date.isoformat(),
        })
    
    return JsonResponse({'versoes': dados})

@login_required
@require_POST
def restaurar_versao(request, pk):
    data_iso = request.POST.get("history_date")
    
    if not data_iso:
        return HttpResponse("Data não enviada", status=400)

    try:
        # O parse_datetime lida com o formato de data que vem do JS
        dt_alvo = parse_datetime(data_iso)
        
        # Busca o registro histórico exato
        registro = Lancamento.history.get(id=pk, history_date=dt_alvo)
        
        # O registro.instance tem os dados de como o lançamento estava naquela data.
        # O .save() vai sobrescrever o atual com os dados antigos.
        registro.instance.save()
        
        resposta = HttpResponse(status=204)
        resposta["HX-Trigger"] = json.dumps({"versaoRestaurada": {"qtd": 1}})
        return resposta
        
    except Exception as e:
        # Retorna o erro real do Python para o JS mostrar
        return HttpResponse(f"Erro: {str(e)}", status=400)