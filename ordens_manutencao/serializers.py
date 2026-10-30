from rest_framework import serializers

from .models import OrdemManutencao, LogOrdemManutencao


class OrdemManutencaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdemManutencao

        fields = [
            'id',
            'ativo',
            'descricao',
            'responsavel',
            'status',
            'custo_estimado',
            'data_abertura',
            'data_conclusao',
        ]

        read_only_fields = [
            'id',
            'data_abertura',
            'data_conclusao',
        ]

    def validate_status(self, value):
        """
        Valida se o status informado pertence às opções do modelo.
        """
        status_validos = [
            escolha[0]
            for escolha in OrdemManutencao.STATUS_CHOICES
        ]

        if value not in status_validos:
            raise serializers.ValidationError(
                "Status de manutenção inválido."
            )

        return value


class LogOrdemManutencaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogOrdemManutencao

        fields = [
            'id',
            'ordem',
            'usuario',
            'acao',
            'descricao',
            'status_anterior',
            'status_novo',
            'data',
        ]

        read_only_fields = [
            'id',
            'ordem',
            'usuario',
            'acao',
            'descricao',
            'status_anterior',
            'status_novo',
            'data',
        ]
