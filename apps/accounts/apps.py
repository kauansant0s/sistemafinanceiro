from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'apps.accounts'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in, user_logged_out
        from .models import LogAcesso

        def registrar_login(sender, request, user, **kwargs):
            LogAcesso.objects.create(usuario=user, acao='login')

        def registrar_logout(sender, request, user, **kwargs):
            if user:
                LogAcesso.objects.create(usuario=user, acao='logout')

        user_logged_in.connect(registrar_login, dispatch_uid='log_login')
        user_logged_out.connect(registrar_logout, dispatch_uid='log_logout')