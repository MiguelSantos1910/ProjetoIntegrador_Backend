from django.core.management.base import BaseCommand, CommandError

from contas.models import LogConta
from backups.services import BackupErro, criar_backup


class Command(BaseCommand):
    help = "Gera um backup do banco em BACKUP_DIR (use no cron do servidor)."

    def handle(self, *args, **options):
        try:
            backup = criar_backup()
        except BackupErro as erro:
            LogConta.objects.create(
                tipo_evento=LogConta.TipoEvento.BACKUP_FALHA,
                descricao=f"Falha no backup pelo terminal: {erro.mensagem}",
            )
            raise CommandError(erro.mensagem) from erro

        LogConta.objects.create(
            tipo_evento=LogConta.TipoEvento.BACKUP_CRIADO,
            descricao=f"Backup {backup['nome']} gerado pelo terminal.",
        )

        contagens = backup["contagens"]
        self.stdout.write(self.style.SUCCESS(f"Backup gerado: {backup['nome']}"))
        self.stdout.write(
            f"  Tamanho: {backup['tamanho_bytes']} bytes | "
            f"Ativos: {contagens['ativos']} | "
            f"Usuários: {contagens['usuarios']} | "
            f"Ordens: {contagens['ordens']}"
        )
