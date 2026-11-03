from django.db import models
from django.conf import settings

class TarefaCalendario(models.Model):
    titulo = models.CharField(max_length=255)
    data = models.DateField()
    done = models.BooleanField(default=False) # <-- ADICIONADO AQUI
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["data"]
        verbose_name = "Tarefa do Calendário"
        verbose_name_plural = "Tarefas do Calendário"

    def save(self, *args, **kwargs):
        self.titulo = self.titulo.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.data.strftime('%d/%m/%Y')} - {self.titulo}"

class RegraCalendario(models.Model):
    TIPO_CHOICES = [
        ('DIAS_UTEIS', 'Dias úteis do mês'),
        ('DIA_FIXO', 'Dia fixo do mês'),
    ]
    titulo = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='DIAS_UTEIS')
    dias = models.IntegerField(help_text="Ex: se for dias úteis, 2 significa os 2 primeiros dias úteis. Se for dia fixo, 10 significa o dia 10.")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.titulo} ({self.dias})"