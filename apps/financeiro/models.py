from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords
from django.conf import settings
import os
from django.utils.text import slugify

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

class Caixa(models.Model):
    nome = models.CharField(max_length=60, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class FormaBaixa(models.Model):
    nome = models.CharField(max_length=60, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "forma de baixa"
        verbose_name_plural = "formas de baixa"

    def __str__(self):
        return self.nome
    
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
    valor_baixado = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name="Valor baixado"
    )
    data_competencia = models.DateField()
    data_vencimento = models.DateField()
    criado_em = models.DateTimeField(auto_now_add=True)

    # Baixa: só existe depois que o lançamento é baixado (data_baixa preenchida = baixado)
    data_baixa = models.DateField(null=True, blank=True)
    liquido = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    caixa = models.ForeignKey(Caixa, null=True, blank=True, on_delete=models.PROTECT, related_name="lancamentos")
    forma_baixa = models.ForeignKey(FormaBaixa, null=True, blank=True, on_delete=models.PROTECT, related_name="lancamentos")
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, blank=True, 
        on_delete=models.SET_NULL, 
        related_name="lancamentos_criados"
    )
    baixado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    history = HistoricalRecords()

    class Meta:
        ordering = ["-data_vencimento", "-id"]
        verbose_name = "lançamento"
        verbose_name_plural = "lançamentos"

    @property
    def baixado(self):
        return self.data_baixa is not None

    @property
    def saldo_restante(self):
        if self.valor_baixado:
            return self.valor - self.valor_baixado
        return self.valor
    
    def save(self, *args, **kwargs):
        self.descricao = self.descricao.upper()
        
        if self.data_baixa:
            if self.valor_baixado is None:
                self.valor_baixado = self.valor
            
            # Se o valor baixado for igual ao valor cheio, o líquido é o próprio valor
            # Se houve desconto (valor_baixado menor), o líquido é o que foi pago
            self.liquido = self.valor_baixado
        else:
            self.liquido = None
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.descricao} ({self.valor})"

def upload_anexo_path(instance, filename):
    # Salva os arquivos numa pasta separada por ID de lançamento
    return f"anexos/lanc_{instance.lancamento.pk}/{filename}"

class AnexoLancamento(models.Model):
    lancamento = models.ForeignKey(Lancamento, on_delete=models.CASCADE, related_name="anexos")
    arquivo = models.FileField(upload_to=upload_anexo_path)
    nome_original = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-criado_em"]

    def save(self, *args, **kwargs):
        if not self.nome_original:
            self.nome_original = os.path.basename(self.arquivo.name)
        super().save(*args, **kwargs)

# Em apps/financeiro/models.py
class BaixaParcial(models.Model):
    lancamento = models.ForeignKey(Lancamento, on_delete=models.CASCADE, related_name='baixas_parciais')
    data_baixa = models.DateField()
    valor_baixado = models.DecimalField(max_digits=12, decimal_places=2)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['data_baixa']

    def __str__(self):
        return f"{self.data_baixa} - R$ {self.valor_baixado}"