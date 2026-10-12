from django.db import models

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
        related_name='ordens_manutencao'
    )
    descricao = models.TextField()

    responsavel = models.CharField(max_length=100)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pendente')

    custo_estimado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    data_abertura = models.DateTimeField(auto_now_add=True)

    data_conclusao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ordem de Manutenção #{self.id} - {self.ativo} - {self.status}"
# Create your models here.
