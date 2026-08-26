from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Ativo, HistoricoMovimentacao
from .permissions import PodeAlterarAtivo
from .serializers import AtivoDetalheSerializer, AtivoSerializer, HistoricoMovimentacaoSerializer


class AtivoViewSet(viewsets.ModelViewSet):
    """
    /api/ativos/            -> listar (com filtro ?status=ATIVO / ?tipo=GABINETE / ?sala=B-111)
    /api/ativos/<id>/       -> detalhe (com histórico)
    /api/ativos/?codigo_qr= -> usado pelo app ao ler o QR Code do ativo
    """

    queryset = Ativo.objects.all().prefetch_related("historico")
    permission_classes = [PodeAlterarAtivo]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "tipo", "sala", "codigo_qr"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AtivoDetalheSerializer
        return AtivoSerializer

    def perform_create(self, serializer):
        ativo = serializer.save()
        HistoricoMovimentacao.objects.create(
            ativo=ativo,
            tipo_evento=HistoricoMovimentacao.TipoEvento.CADASTRO,
            descricao="Ativo cadastrado no sistema.",
            usuario=self.request.user if self.request.user.is_authenticated else None,
        )


class HistoricoMovimentacaoViewSet(viewsets.ModelViewSet):
    queryset = HistoricoMovimentacao.objects.all()
    serializer_class = HistoricoMovimentacaoSerializer
    permission_classes = [IsAuthenticated, PodeAlterarAtivo]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["ativo", "tipo_evento"]

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user if self.request.user.is_authenticated else None)
