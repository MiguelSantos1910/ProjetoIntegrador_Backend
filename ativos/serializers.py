from rest_framework import serializers

from .models import Ativo, HistoricoMovimentacao


class HistoricoMovimentacaoSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.username", read_only=True, default=None)

    class Meta:
        model = HistoricoMovimentacao
        fields = ["id", "ativo", "tipo_evento", "descricao", "usuario", "usuario_nome", "data"]
        read_only_fields = ["data"]


class AtivoSerializer(serializers.ModelSerializer):
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
        read_only_fields = ["codigo_qr", "data_cadastro", "atualizado_em"]


class AtivoDetalheSerializer(AtivoSerializer):
    """Usado na tela de Detalhes do Equipamento: inclui o histórico completo."""

    historico = HistoricoMovimentacaoSerializer(many=True, read_only=True)

    class Meta(AtivoSerializer.Meta):
        fields = AtivoSerializer.Meta.fields + ["historico"]
