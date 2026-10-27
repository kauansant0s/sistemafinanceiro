from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, LogAcesso


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Extras", {"fields": ("nome_completo", "telefone", "cargo", "foto")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Extras", {"fields": ("nome_completo", "telefone", "cargo")}),
    )
    list_display = ("username", "nome_completo", "email", "cargo", "is_active")
    list_filter = UserAdmin.list_filter + ("cargo",)


@admin.register(LogAcesso)
class LogAcessoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "acao", "data")
    list_filter = ("acao",)
    date_hierarchy = "data"