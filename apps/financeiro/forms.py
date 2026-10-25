import unicodedata
from decimal import Decimal, InvalidOperation

from django import forms

from .models import Centro, ContaFinanceira, Lancamento

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