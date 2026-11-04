from django.core.management.base import BaseCommand, CommandError

from contas.models import LogConta
from backups.services import BackupErro, listar_backups, restaurar_backup


class Command(BaseCommand):
    help = (
        "Restaura o banco a partir de um backup de BACKUP_DIR. "
        "Sem argumento, lista os backups disponíveis."
    )

    def add_arguments(self, parser):
        parser.add_argument("nome", nargs="?", help="Ex.: db_20261104_140000.sqlite3")
        parser.add_argument(
            "--sim",
            action="store_true",
            help="Não pede confirmação.",
        )

    def handle(self, *args, nome=None, sim=False, **options):
        if not nome:
            for backup in listar_backups():
                contagens = backup["contagens"] or {}
                self.stdout.write(
                    f"{backup['nome']}  ativos={contagens.get('ativos')} "
                    f"usuarios={contagens.get('usuarios')} "
                    f"ordens={contagens.get('ordens')}"
                )
            return

        if not sim:
            resposta = input(
                f"O banco inteiro voltará ao estado de {nome}. "
                "Digite RESTAURAR para continuar: "
            )
            if resposta.strip() != "RESTAURAR":
                raise CommandError("Restauração cancelada.")

        try:
            resultado = restaurar_backup(nome)
        except BackupErro as erro:
            LogConta.objects.create(
                tipo_evento=LogConta.TipoEvento.BACKUP_FALHA,
                descricao=f"Falha ao restaurar {nome} pelo terminal: {erro.mensagem}",
            )
            raise CommandError(erro.mensagem) from erro

        seguranca = resultado["backup_seguranca"]["nome"]

        LogConta.objects.create(
            tipo_evento=LogConta.TipoEvento.BACKUP_RESTAURADO,
            descricao=(
                f"Banco restaurado a partir de {nome} pelo terminal. "
                f"Estado anterior salvo em {seguranca}."
            ),
        )

        contagens = resultado["restaurado"]["contagens"]
        self.stdout.write(self.style.SUCCESS(f"Banco restaurado a partir de {nome}"))
        self.stdout.write(f"  Estado anterior salvo em: {seguranca}")
        self.stdout.write(
            f"  Ativos: {contagens['ativos']} | Usuários: {contagens['usuarios']} | "
            f"Ordens: {contagens['ordens']}"
        )
