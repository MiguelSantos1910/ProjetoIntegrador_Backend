
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import OrdemManutencao, LogOrdemManutencao
from .serializers import (
    OrdemManutencaoSerializer,
    LogOrdemManutencaoSerializer,
)


class OrdemManutencaoViewSet(viewsets.ModelViewSet):
    queryset = OrdemManutencao.objects.select_related('ativo').all()
    serializer_class = OrdemManutencaoSerializer

    def perform_create(self, serializer):
        ordem = serializer.save()

        usuario = self.request.user
        if not usuario.is_authenticated:
            usuario = None

        LogOrdemManutencao.objects.create(
            ordem=ordem,
            usuario=usuario,
            acao='Criada',
            descricao='Ordem de manutenção criada.',
            status_anterior='',
            status_novo=ordem.status,
        )

    def perform_update(self, serializer):
        ordem = self.get_object()
        status_anterior = ordem.status

        ordem = serializer.save()

        usuario = self.request.user
        if not usuario.is_authenticated:
            usuario = None

        if status_anterior != ordem.status:
            LogOrdemManutencao.objects.create(
                ordem=ordem,
                usuario=usuario,
                acao='Status alterado',
                descricao=(
                    f'Status alterado de "{status_anterior}" '
                    f'para "{ordem.status}".'
                ),
                status_anterior=status_anterior,
                status_novo=ordem.status,
            )
        else:
            LogOrdemManutencao.objects.create(
                ordem=ordem,
                usuario=usuario,
                acao='Atualizada',
                descricao='Dados da ordem de manutenção atualizados.',
                status_anterior=status_anterior,
                status_novo=ordem.status,
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_logs_ordem(request, ordem_id):
    logs = LogOrdemManutencao.objects.filter(
        ordem_id=ordem_id
    ).select_related('usuario', 'ordem')

    serializer = LogOrdemManutencaoSerializer(
        logs,
        many=True,
    )

    return Response(serializer.data)
