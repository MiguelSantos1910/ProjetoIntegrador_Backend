from django.db import migrations


def vazio_para_nulo(apps, schema_editor):
    """Patrimônio em branco passa a ser NULL (o campo é único e opcional)."""
    Ativo = apps.get_model("ativos", "Ativo")
    Ativo.objects.filter(numero_patrimonio="").update(numero_patrimonio=None)


class Migration(migrations.Migration):

    dependencies = [
        ("ativos", "0004_historico_mudanca_sala"),
    ]

    operations = [
        migrations.RunPython(vazio_para_nulo, migrations.RunPython.noop),
    ]
