from decimal import Decimal

from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.http import require_http_methods
from .forms import FiltroLancamentosForm, LancamentoEdicaoForm, LancamentoForm, normalizar
from .models import ContaFinanceira, Lancamento, SubCentro


def _subcentros_do_centro(centro_id):
    if centro_id and str(centro_id).isdigit():
        return SubCentro.objects.filter(centro_id=centro_id)
    return SubCentro.objects.none()


@login_required
def novo_lancamento(request):
    if request.method == "POST":
        form = LancamentoForm(request.POST)
        if form.is_valid():
            form.save()
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