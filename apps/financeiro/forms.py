import unicodedata
from decimal import Decimal, InvalidOperation
from django import forms
from .models import Centro, ContaFinanceira, Lancamento, SubCentro

DATA_BR = ["%d/%m/%Y"]


class LancamentoForm(forms.ModelForm):
    # "centro" não existe no Lançamento (ele só guarda o sub-centro),
    # mas o formulário precisa dele para conferir se os dois combinam.
    centro = forms.ModelChoiceField(queryset=Centro.objects.all())
    valor = forms.CharField()
    data_competencia = forms.DateField(input_formats=DATA_BR)
    data_vencimento = forms.DateField(input_formats=DATA_BR)

    class Meta:
        model = Lancamento
        fields = [
            "centro", "subcentro", "conta", "descricao", "observacoes",
            "nota_fiscal_ano", "nota_fiscal_numero",
            "valor", "data_competencia", "data_vencimento",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["conta"].queryset = ContaFinanceira.objects.filter(ativa=True)

    def clean_valor(self):
        bruto = self.cleaned_data["valor"]
        limpo = bruto.replace("R$", "").replace(".", "").replace(",", ".").strip()
        try:
            valor = Decimal(limpo)
        except InvalidOperation:
            raise forms.ValidationError("Informe um valor válido.")
        if valor <= 0:
            raise forms.ValidationError("O valor deve ser maior que zero.")
        return valor

    def clean(self):
        dados = super().clean()
        centro = dados.get("centro")
        subcentro = dados.get("subcentro")
        if centro and subcentro and subcentro.centro_id != centro.id:
            self.add_error("subcentro", "Este sub-centro não pertence ao centro escolhido.")
        return dados


def normalizar(texto):
    """Minúsculas e sem acento, para a busca achar 'convenio' em 'Convênio'."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()

def _valor_br(texto):
    """Converte 'R$ 1.234,56' em Decimal. Vazio vira None."""
    texto = (texto or "").strip()
    if not texto:
        return None
    limpo = texto.replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return Decimal(limpo)
    except InvalidOperation:
        raise forms.ValidationError("Informe um valor válido.")


class FiltroLancamentosForm(forms.Form):
    CAMPOS_DATA = {
        "vencimento": "data_vencimento",
        "competencia": "data_competencia",
        "lancamento": "criado_em__date",
    }

    centro = forms.ModelChoiceField(queryset=Centro.objects.all(), required=False)
    subcentro = forms.ModelChoiceField(queryset=SubCentro.objects.all(), required=False)
    tipo = forms.ChoiceField(choices=[("", "Todos")] + ContaFinanceira.Tipo.choices, required=False)
    data_campo = forms.ChoiceField(choices=[(k, k) for k in CAMPOS_DATA], required=False)
    data_inicial = forms.DateField(input_formats=DATA_BR, required=False)
    data_final = forms.DateField(input_formats=DATA_BR, required=False)
    valor_min = forms.CharField(required=False)
    valor_max = forms.CharField(required=False)
    descricao = forms.CharField(required=False)
    nota = forms.CharField(required=False)
    observacao = forms.CharField(required=False)

    def clean_valor_min(self):
        return _valor_br(self.cleaned_data["valor_min"])

    def clean_valor_max(self):
        return _valor_br(self.cleaned_data["valor_max"])

    def filtrar(self, qs):
        d = self.cleaned_data
        if d.get("centro"):
            qs = qs.filter(subcentro__centro=d["centro"])
        if d.get("subcentro"):
            qs = qs.filter(subcentro=d["subcentro"])
        if d.get("tipo"):
            qs = qs.filter(conta__tipo=d["tipo"])

        campo = self.CAMPOS_DATA[d.get("data_campo") or "vencimento"]
        if d.get("data_inicial"):
            qs = qs.filter(**{f"{campo}__gte": d["data_inicial"]})
        if d.get("data_final"):
            qs = qs.filter(**{f"{campo}__lte": d["data_final"]})

        if d.get("valor_min") is not None:
            qs = qs.filter(valor__gte=d["valor_min"])
        if d.get("valor_max") is not None:
            qs = qs.filter(valor__lte=d["valor_max"])

        if d.get("descricao"):
            qs = qs.filter(descricao__icontains=d["descricao"])
        if d.get("observacao"):
            qs = qs.filter(observacoes__icontains=d["observacao"])
        if d.get("nota"):
            qs = qs.filter(nota_fiscal_numero__icontains=d["nota"])
        return qs