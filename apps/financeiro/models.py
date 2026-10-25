from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords


class Centro(models.Model):
    nome = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class SubCentro(models.Model):
    centro = models.ForeignKey(Centro, on_delete=models.PROTECT, related_name="subcentros")
    nome = models.CharField(max_length=50)

    class Meta:
        ordering = ["centro__nome", "nome"]
        verbose_name = "sub-centro"
        verbose_name_plural = "sub-centros"
        constraints = [
            models.UniqueConstraint(fields=["centro", "nome"], name="subcentro_unico_por_centro"),
        ]

    def __str__(self):
        return f"{self.centro} / {self.nome}"


class ContaFinanceira(models.Model):
    class Tipo(models.TextChoices):
        RECEITA = "R", "Receita"
        DESPESA = "D", "Despesa"

    codigo = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=1, choices=Tipo.choices)
    nome = models.CharField(max_length=100)
    ativa = models.BooleanField(default=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["codigo"]
        verbose_name = "conta financeira"
        verbose_name_plural = "contas financeiras"

    def __str__(self):
        return f"{self.codigo} - {self.get_tipo_display()} - {self.nome}"


class Lancamento(models.Model):
    subcentro = models.ForeignKey(SubCentro, on_delete=models.PROTECT, related_name="lancamentos")
    conta = models.ForeignKey(ContaFinanceira, on_delete=models.PROTECT, related_name="lancamentos")
    descricao = models.CharField(max_length=255)
    observacoes = models.TextField(blank=True)
    nota_fiscal_ano = models.PositiveSmallIntegerField(null=True, blank=True)
    nota_fiscal_numero = models.CharField(max_length=30, blank=True)
    valor = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    data_competencia = models.DateField()
    data_vencimento = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-data_vencimento", "-id"]
        verbose_name = "lançamento"
        verbose_name_plural = "lançamentos"

    def save(self, *args, **kwargs):
        self.descricao = self.descricao.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.descricao} ({self.valor})"