from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    CARGO_CHOICES = [
        ('setor', 'Setor'),
        ('faturamento', 'Faturamento'),
        ('financeiro', 'Financeiro'),
        ('gerencia', 'Gerência'),
    ]
    
    # Usando first_name para o nome completo, ou adicionando um campo específico:
    nome_completo = models.CharField('Nome completo', max_length=150, blank=True)
    telefone = models.CharField('Telefone', max_length=20, blank=True)
    cargo = models.CharField('Tipo de usuário', max_length=20, choices=CARGO_CHOICES, default='financeiro')
    foto = models.ImageField('Foto de perfil', upload_to='perfis/', null=True, blank=True)

    def __str__(self):
        return self.nome_completo or self.username

class LogAcesso(models.Model):
    TIPO_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    acao = models.CharField(max_length=20, choices=TIPO_CHOICES)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data']
        verbose_name = 'Log de Acesso'
        verbose_name_plural = 'Logs de Acesso'

    def __str__(self):
        return f"{self.usuario} - {self.acao} em {self.data}"