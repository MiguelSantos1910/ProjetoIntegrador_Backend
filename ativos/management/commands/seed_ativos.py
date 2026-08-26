from django.core.management.base import BaseCommand

from ativos.models import Ativo, HistoricoMovimentacao


class Command(BaseCommand):
    """
    Popula o banco com o escopo de teste definido no Documento 1:
    4 gabinetes, 4 monitores, 4 teclados e 4 mesas da sala B-111.

    Os números de patrimônio abaixo são só placeholders (PAT-...) —
    troque pelos números reais do inventário patrimonial que vocês têm
    em mãos antes de usar isso como dado "de verdade". Teclados ficam
    sem número de patrimônio de propósito, igual ao inventário oficial.

    Uso: python manage.py seed_ativos
    """

    help = "Cria os 16 ativos de teste (4 gabinetes, 4 monitores, 4 teclados, 4 mesas) da sala B-111."

    def handle(self, *args, **options):
        itens = [
            *[(Ativo.Tipo.GABINETE, "WORKSTATION CORPORATIVO", f"PAT-GAB-{i:02d}") for i in range(1, 5)],
            *[(Ativo.Tipo.MONITOR, 'MONITOR DE VÍDEO 24" DELL', f"PAT-MON-{i:02d}") for i in range(1, 5)],
            # Teclados não têm número de patrimônio oficial: o "#i" no final da
            # descrição garante que os 4 fiquem distintos aqui (senão o
            # get_or_create abaixo trataria os 4 como o mesmo registro).
            *[(Ativo.Tipo.TECLADO, f"TECLADO USB PADRÃO ABNT2 #{i}", None) for i in range(1, 5)],
            *[(Ativo.Tipo.MESA, "MESA DE INFORMÁTICA 1200 CINZA", f"PAT-MESA-{i:02d}") for i in range(1, 5)],
        ]

        criados = 0
        for tipo, descricao, numero_patrimonio in itens:
            ativo, foi_criado = Ativo.objects.get_or_create(
                tipo=tipo,
                descricao=descricao,
                numero_patrimonio=numero_patrimonio,
                defaults={"sala": "B-111"},
            )
            if foi_criado:
                criados += 1
                HistoricoMovimentacao.objects.create(
                    ativo=ativo,
                    tipo_evento=HistoricoMovimentacao.TipoEvento.CADASTRO,
                    descricao="Ativo criado pelo comando de seed (dado de teste).",
                )

        self.stdout.write(self.style.SUCCESS(f"{criados} ativo(s) criado(s). Total no banco: {Ativo.objects.count()}."))
