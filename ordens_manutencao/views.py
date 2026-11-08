from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import OrdemManutencao, LogOrdemManutencao
from .serializers import (
    OrdemManutencaoSerializer,
    LogOrdemManutencaoSerializer,
)
from .permissions import (
    PodeAlterarOrdemManutencao,
    PodeConsultarLogOrdem,
)


class OrdemManutencaoViewSet(viewsets.ModelViewSet):
    queryset = OrdemManutencao.objects.select_related(
        'ativo'
    ).all()

    serializer_class = OrdemManutencaoSerializer
    permission_classes = [PodeAlterarOrdemManutencao]

    # Campos comparados para descrever o que mudou numa atualização.
    CAMPOS_REGISTRADOS = {
        'descricao': 'descrição',
        'responsavel': 'responsável',
        'custo_estimado': 'custo estimado',
    }

    def perform_create(self, serializer):
        # Ordem já aberta como concluída recebe a data de conclusão.
        if serializer.validated_data.get('status') == 'Concluída':
            ordem = serializer.save(data_conclusao=timezone.now())
        else:
            ordem = serializer.save()

        usuario = self.request.user

        LogOrdemManutencao.objects.create(
            ordem=ordem,
            usuario=usuario if usuario.is_authenticated else None,
            acao='Criada',
            descricao='Ordem de manutenção criada.',
            status_anterior='',
            status_novo=ordem.status,
        )

    def perform_update(self, serializer):
        ordem = self.get_object()
        status_anterior = ordem.status
        valores_anteriores = {
            campo: getattr(ordem, campo)
            for campo in self.CAMPOS_REGISTRADOS
        }

        ordem = serializer.save()

        alterados = [
            rotulo
            for campo, rotulo in self.CAMPOS_REGISTRADOS.items()
            if getattr(ordem, campo) != valores_anteriores[campo]
        ]

        usuario = self.request.user

        # Atualiza a data de conclusão conforme o status.
        if ordem.status == 'Concluída':
            if status_anterior != 'Concluída':
                ordem.data_conclusao = timezone.now()
                ordem.save(update_fields=['data_conclusao'])

        elif status_anterior == 'Concluída':
            ordem.data_conclusao = None
            ordem.save(update_fields=['data_conclusao'])

        # Registra a alteração no histórico.
        if status_anterior != ordem.status:
            LogOrdemManutencao.objects.create(
                ordem=ordem,
                usuario=usuario if usuario.is_authenticated else None,
                acao='Status alterado',
                descricao=(
                    f'Status alterado de "{status_anterior}" '
                    f'para "{ordem.status}".'
                ),
                status_anterior=status_anterior,
                status_novo=ordem.status,
            )

        if alterados:
            LogOrdemManutencao.objects.create(
                ordem=ordem,
                usuario=usuario if usuario.is_authenticated else None,
                acao='Atualizada',
                descricao=f'Campos alterados: {", ".join(alterados)}.',
                status_anterior=status_anterior,
                status_novo=ordem.status,
            )

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied(
            'As ordens de manutenção não podem ser excluídas.'
        )


@api_view(['GET'])
@permission_classes([
    IsAuthenticated,
    PodeConsultarLogOrdem,
])
def listar_logs_ordem(request, ordem_id):
    get_object_or_404(OrdemManutencao, pk=ordem_id)

    logs = LogOrdemManutencao.objects.filter(
        ordem_id=ordem_id
    ).select_related('usuario', 'ordem')

    serializer = LogOrdemManutencaoSerializer(
        logs,
        many=True,
    )

    return Response(serializer.data)
