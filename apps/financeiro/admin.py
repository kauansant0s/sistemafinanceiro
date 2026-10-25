from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Centro, ContaFinanceira, Lancamento, SubCentro


@admin.register(Centro)
class CentroAdmin(admin.ModelAdmin):
    list_display = ("nome",)


@admin.register(SubCentro)
class SubCentroAdmin(admin.ModelAdmin):
    list_display = ("nome", "centro")
    list_filter = ("centro",)


@admin.register(ContaFinanceira)
class ContaFinanceiraAdmin(SimpleHistoryAdmin):
    list_display = ("codigo", "tipo", "nome", "ativa")
    list_filter = ("tipo", "ativa")
    search_fields = ("codigo", "nome")


@admin.register(Lancamento)
class LancamentoAdmin(SimpleHistoryAdmin):
    list_display = ("data_vencimento", "descricao", "conta", "subcentro", "valor")
    list_filter = ("subcentro__centro", "subcentro", "conta__tipo")
    search_fields = ("descricao", "nota_fiscal_numero")
    date_hierarchy = "data_vencimento"