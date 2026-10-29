
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Ativo, HistoricoMovimentacao
from .permissions import PodeAlterarAtivo
from .serializers import (
    AtivoDetalheSerializer,
    AtivoSerializer,
    HistoricoMovimentacaoSerializer,
)


class AtivoViewSet(viewsets.ModelViewSet):
    """
    /api/ativos/             -> listar e filtrar ativos
    /api/ativos/<id>/        -> detalhes com histórico
    /api/ativos/?codigo_qr=  -> localizar ativo pelo QR Code
    """

    queryset = Ativo.objects.all().prefetch_related("historico")
    permission_classes = [PodeAlterarAtivo]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "status",
        "tipo",
        "sala",
        "codigo_qr",
    ]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AtivoDetalheSerializer

        return AtivoSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        ativo = serializer.save()

        HistoricoMovimentacao.objects.create(
            ativo=ativo,
            tipo_evento=HistoricoMovimentacao.TipoEvento.CADASTRO,
            descricao="Ativo cadastrado no sistema.",
            usuario=self.request.user,
        )

    @transaction.atomic
    def perform_update(self, serializer):
        ativo = serializer.save()

        # Não cria eventos genéricos para qualquer edição.
        # Movimentações específicas devem ser registradas
        # pelas respectivas operações de negócio.

    def destroy(self, request, *args, **kwargs):
        """
        Evita exclusão física para preservar o histórico.
        O ativo deve ser inativado por uma operação específica.
        """
        raise PermissionDenied(
            "A exclusão física de ativos não é permitida. "
            "Utilize a operação de inativação."
        )


class HistoricoMovimentacaoViewSet(viewsets.ModelViewSet):
    """
    Histórico somente para consulta pela API.
    Os eventos são registrados pelas operações de negócio.
    """

    queryset = HistoricoMovimentacao.objects.select_related(
        "ativo",
        "usuario",
    ).all()

    serializer_class = HistoricoMovimentacaoSerializer
    permission_classes = [
        IsAuthenticated,
        PodeAlterarAtivo,
    ]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        "ativo",
        "tipo_evento",
    ]

    def create(self, request, *args, **kwargs):
        raise PermissionDenied(
            "O histórico deve ser registrado por uma ação autorizada do sistema."
        )

    def update(self, request, *args, **kwargs):
        raise PermissionDenied(
            "O histórico não pode ser alterado."
        )

    def partial_update(self, request, *args, **kwargs):
        raise PermissionDenied(
            "O histórico não pode ser alterado."
        )

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied(
            "O histórico não pode ser excluído."
        )
