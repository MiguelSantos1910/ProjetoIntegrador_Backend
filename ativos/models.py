import uuid

from django.conf import settings
from django.db import models


class Ativo(models.Model):
    """
    Um item físico do inventário do laboratório B-111.
    Escopo de teste do projeto (Documento 1): 4 gabinetes, 4 monitores,
    4 teclados e 4 mesas. Teclados não têm número de patrimônio no
    inventário oficial do SENAI — por isso o campo é opcional.
    """

    class Tipo(models.TextChoices):
        GABINETE = "GABINETE", "Gabinete"
        MONITOR = "MONITOR", "Monitor"
        TECLADO = "TECLADO", "Teclado"
        MESA = "MESA", "Mesa"

    class Status(models.TextChoices):
        ATIVO = "ATIVO", "Ativo"
        EM_MANUTENCAO = "EM_MANUTENCAO", "Em manutenção"
        DEVOLVIDO = "DEVOLVIDO", "Devolvido"

    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    descricao = models.CharField(
        max_length=200,
        help_text='Ex.: "WORKSTATION CORPORATIVO", "MONITOR DE VÍDEO 24\" DELL"',
    )
    numero_patrimonio = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        help_text="Número do inventário patrimonial oficial do SENAI. Em branco para teclados (não constam no inventário oficial).",
    )
    codigo_qr = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Identificador único gerado pelo sistema — é o que vira o QR Code colado no ativo.",
    )
    sala = models.CharField(max_length=20, default="B-111")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ATIVO)

    # Usados pela funcionalidade de mapa (atividade L5.2) — deixados aqui desde já
    # para não exigir uma migração nova mais pra frente. Ficam nulos até lá.
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    data_cadastro = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipo", "descricao"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.descricao} ({self.numero_patrimonio or self.codigo_qr})"


class HistoricoMovimentacao(models.Model):
    """
    Registro de cada evento relevante de um ativo (entrega, devolução,
    manutenção, cadastro). É o que alimenta a tela "Detalhes do Equipamento"
    (item E da situação de aprendizagem "S&M Ativos") com o histórico.
    """

    class TipoEvento(models.TextChoices):
        CADASTRO = "CADASTRO", "Cadastro"
        ENTREGA = "ENTREGA", "Entrega"
        DEVOLUCAO = "DEVOLUCAO", "Devolução"
        MANUTENCAO = "MANUTENCAO", "Manutenção"

    ativo = models.ForeignKey(Ativo, on_delete=models.CASCADE, related_name="historico")
    tipo_evento = models.CharField(max_length=20, choices=TipoEvento.choices)
    descricao = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data"]

    def __str__(self):
        return f"{self.ativo} — {self.get_tipo_evento_display()} em {self.data:%d/%m/%Y}"
