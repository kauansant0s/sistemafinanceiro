from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # Rotas de Autenticação (Login/Logout)
    path("", include("apps.accounts.urls")),
    
    # Rotas da Página Inicial e Calendário (Core)
    path("", include("apps.core.urls")),
    
    # Rotas do Financeiro (Lançamentos, Anexos, etc)
    path("", include("apps.financeiro.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)