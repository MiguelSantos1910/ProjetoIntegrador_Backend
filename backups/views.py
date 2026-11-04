from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from contas.models import LogConta
from contas.views import obter_ip, usuario_eh_professor

from .services import (
    BackupErro,
    criar_backup,
    listar_backups,
    restaurar_backup,
)


CONFIRMACAO_RESTAURAR = "RESTAURAR"


class PodeGerenciarBackup(BasePermission):
    """Backup e restauração: somente professor ou superusuário."""

    message = "Somente professores podem gerenciar backups."

    def has_permission(self, request, view):
        return usuario_eh_professor(request.user)


def registrar_log(request, tipo_evento, descricao, usuario=None):
    LogConta.objects.create(
        usuario=usuario if usuario is not None else request.user,
        tipo_evento=tipo_evento,
        descricao=descricao,
        ip=obter_ip(request),
    )


def resposta_erro(request, erro, acao):
    registrar_log(
        request,
        LogConta.TipoEvento.BACKUP_FALHA,
        f"Falha ao {acao}: {erro.mensagem}",
    )

    return Response({"detail": erro.mensagem}, status=erro.status)


# ---------------------------------------------------------------------------
# GET  /api/backups/  → lista os backups
# POST /api/backups/  → gera um backup agora
# ---------------------------------------------------------------------------

class BackupListCreateView(APIView):
    permission_classes = [IsAuthenticated, PodeGerenciarBackup]

    def get(self, request):
        try:
            return Response(listar_backups())
        except BackupErro as erro:
            return Response({"detail": erro.mensagem}, status=erro.status)

    def post(self, request):
        try:
            backup = criar_backup()
        except BackupErro as erro:
            return resposta_erro(request, erro, "gerar backup")

        registrar_log(
            request,
            LogConta.TipoEvento.BACKUP_CRIADO,
            f"Backup {backup['nome']} gerado pelo painel.",
        )

        return Response(backup, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# POST /api/backups/<nome>/restaurar/   body: {"confirmacao": "RESTAURAR"}
# ---------------------------------------------------------------------------

class BackupRestaurarView(APIView):
    permission_classes = [IsAuthenticated, PodeGerenciarBackup]

    def post(self, request, nome):
        if request.data.get("confirmacao") != CONFIRMACAO_RESTAURAR:
            return Response(
                {
                    "detail": (
                        "Confirme a restauração enviando "
                        f'"confirmacao": "{CONFIRMACAO_RESTAURAR}".'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = request.user.username
        usuario_id = request.user.pk

        try:
            resultado = restaurar_backup(nome)
        except BackupErro as erro:
            return resposta_erro(request, erro, f"restaurar {nome}")

        # O log é gravado DEPOIS de restaurar; antes, ele seria apagado junto
        # com os logs antigos. O usuário pode não existir no backup restaurado.
        registrar_log(
            request,
            LogConta.TipoEvento.BACKUP_RESTAURADO,
            (
                f"Banco restaurado a partir de {nome} por {username}. "
                "Estado anterior salvo em "
                f"{resultado['backup_seguranca']['nome']}."
            ),
            usuario=User.objects.filter(pk=usuario_id).first(),
        )

        return Response(resultado)
