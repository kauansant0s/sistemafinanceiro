from django.urls import path
from . import views

app_name = "core"  # <--- ADICIONE ISSO

urlpatterns = [
    path("", views.home, name="home"),  # <--- ADICIONE ISSO
    path('calendario/', views.api_tarefas_calendario, name='api_tarefas_calendario'),
    path('calendario/salvar/', views.salvar_tarefa_calendario, name='salvar_tarefa_calendario'),
    path('calendario/editar/<int:pk>/', views.editar_tarefa_calendario, name='editar_tarefa_calendario'),
    path('calendario/excluir/<int:pk>/', views.excluir_tarefa_calendario, name='excluir_tarefa_calendario'),
    path('regras/', views.api_regras_calendario, name='api_regras_calendario'),
    path('regras/salvar/', views.salvar_regra_calendario, name='salvar_regra_calendario'),
    path('regras/excluir/<int:pk>/', views.excluir_regra_calendario, name='excluir_regra_calendario'),
]