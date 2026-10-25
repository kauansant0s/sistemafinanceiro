from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.vary import vary_on_headers

from .forms import FiltroLancamentosForm, LancamentoForm, normalizar
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
    form = FiltroLancamentosForm(request.GET or None)
    qs = Lancamento.objects.select_related("subcentro__centro", "conta")

    if form.is_bound:
        qs = form.filtrar(qs) if form.is_valid() else qs.none()

    totais = qs.aggregate(
        receitas=Sum("valor", filter=Q(conta__tipo="R")),
        despesas=Sum("valor", filter=Q(conta__tipo="D")),
    )
    receitas = totais["receitas"] or Decimal("0")
    despesas = totais["despesas"] or Decimal("0")

    pagina = Paginator(qs, 50).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    contexto = {
        "form": form,
        "pagina": pagina,
        "querystring": params.urlencode(),
        "receitas": receitas,
        "despesas": despesas,
        "saldo": receitas - despesas,
    }

    # Só devolve o pedaço da tabela quando é o HTMX pedindo
    # (e não quando o navegador restaura o histórico, que precisa da página inteira).
    if request.htmx and not request.htmx.history_restore_request:
        return render(request, "partials/tabela_lancamentos.html", contexto)

    contexto["subcentros"] = _subcentros_do_centro(request.GET.get("centro"))
    contexto["subcentro_selecionado"] = request.GET.get("subcentro")
    return render(request, "financeiro/lancamentos.html", contexto)