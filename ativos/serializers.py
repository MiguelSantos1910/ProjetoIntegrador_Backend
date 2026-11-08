
from rest_framework import serializers

from .models import Ativo, HistoricoMovimentacao


class HistoricoMovimentacaoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(
        source="usuario.username",
        read_only=True,
        default=None,
    )

    class Meta:
        model = HistoricoMovimentacao
        fields = [
            "id",
            "ativo",
            "tipo_evento",
            "descricao",
            "usuario",
            "usuario_nome",
            "data",
        ]
        read_only_fields = [
            "id",
            "usuario",
            "usuario_nome",
            "data",
        ]


class AtivoSerializer(serializers.ModelSerializer):
    # Intervalos geográficos válidos (o modelo só limita a quantidade de
    # dígitos, o que aceitaria latitude 500, por exemplo).
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=-90,
        max_value=90,
        required=False,
        allow_null=True,
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=-180,
        max_value=180,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Ativo
        fields = [
            "id",
            "tipo",
            "descricao",
            "numero_patrimonio",
            "codigo_qr",
            "sala",
            "status",
            "latitude",
            "longitude",
            "data_cadastro",
            "atualizado_em",
        ]
        read_only_fields = [
            "id",
            "codigo_qr",
            "data_cadastro",
            "atualizado_em",
        ]

    def to_internal_value(self, data):
        """
        Patrimônio vazio vira NULL antes da validação de unicidade.

        O campo é único e opcional: dois ativos sem patrimônio enviados como
        "" geravam IntegrityError (erro 500). Com NULL, o banco permite
        vários ativos sem patrimônio.
        """
        if hasattr(data, "copy") and "numero_patrimonio" in data:
            valor = data.get("numero_patrimonio")

            if valor is None or (isinstance(valor, str) and not valor.strip()):
                data = data.copy()
                data["numero_patrimonio"] = None

            elif isinstance(valor, str) and valor != valor.strip():
                data = data.copy()
                data["numero_patrimonio"] = valor.strip()

        return super().to_internal_value(data)


class AtivoDetalheSerializer(AtivoSerializer):
    """Usado na tela de detalhes do equipamento: inclui o histórico."""

    historico = HistoricoMovimentacaoSerializer(
        many=True,
        read_only=True,
    )

    class Meta(AtivoSerializer.Meta):
        fields = AtivoSerializer.Meta.fields + ["historico"]
