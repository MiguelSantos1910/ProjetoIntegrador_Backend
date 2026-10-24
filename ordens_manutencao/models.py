
from django.db import models
from django.conf import settings


class OrdemManutencao(models.Model):
    STATUS_CHOICES = [
        ('Pendente', 'Pendente'),
        ('Em andamento', 'Em andamento'),
        ('Concluída', 'Concluída'),
        ('Cancelada', 'Cancelada'),
    ]

    ativo = models.ForeignKey(
        'ativos.Ativo',
        on_delete=models.PROTECT,
        related_name='ordens_manutencao',
    )

    descricao = models.TextField()
    responsavel = models.CharField(max_length=100)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pendente',
    )

    custo_estimado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    data_abertura = models.DateTimeField(auto_now_add=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f'Ordem de Manutenção #{self.id} - '
            f'{self.ativo} - {self.status}'
        )


class LogOrdemManutencao(models.Model):
    ACAO_CHOICES = [
        ('Criada', 'Ordem criada'),
        ('Status alterado', 'Status alterado'),
        ('Atualizada', 'Ordem atualizada'),
    ]

    ordem = models.ForeignKey(
        OrdemManutencao,
        on_delete=models.PROTECT,
        related_name='logs',
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs_ordens_manutencao',
    )

    acao = models.CharField(
        max_length=30,
        choices=ACAO_CHOICES,
    )

    descricao = models.TextField()

    status_anterior = models.CharField(
        max_length=20,
        blank=True,
        default='',
    )

    status_novo = models.CharField(
        max_length=20,
        blank=True,
        default='',
    )

    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data']

    def __str__(self):
        return f'Log da ordem #{self.ordem_id} - {self.acao}'
