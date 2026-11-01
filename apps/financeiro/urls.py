from django.urls import path

from . import views

app_name = "financeiro"

urlpatterns = [
    path("lancamentos/novo/", views.novo_lancamento, name="novo_lancamento"),
    path("lancamentos/subcentros/", views.subcentros, name="subcentros"),
    path("lancamentos/contas/", views.buscar_contas, name="buscar_contas"),
    path("lancamentos/", views.lancamentos, name="lancamentos"),
    path("lancamentos/<int:pk>/", views.lancamento_linha, name="lancamento_linha"),
    path("lancamentos/<int:pk>/editar/", views.lancamento_editar, name="lancamento_editar"),
    path("importacoes/", views.importacoes, name="importacoes"),
    path("lancamentos/baixar/", views.baixar_lancamentos, name="baixar_lancamentos"),
    path("caixas/novo/", views.criar_caixa, name="criar_caixa"),
    path("formas-baixa/novo/", views.criar_forma_baixa, name="criar_forma_baixa"),
    path("lancamentos/excluir/", views.excluir_lancamentos, name="excluir_lancamentos"),
    path("lancamentos/desfazer-exclusao/", views.desfazer_exclusao, name="desfazer_exclusao"),
]