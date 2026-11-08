from rest_framework import serializers

from ativos.models import Ativo

from .models import OrdemManutencao, LogOrdemManutencao


class OrdemManutencaoSerializer(serializers.ModelSerializer):
    custo_estimado = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )

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

        ordem = self.instance

        # Ordem cancelada é encerrada: para retomar o serviço, abre-se outra.
        if (
            ordem is not None
            and ordem.status == 'Cancelada'
            and value != 'Cancelada'
        ):
            raise serializers.ValidationError(
                "Uma ordem cancelada não pode ser reaberta. "
                "Abra uma nova ordem de manutenção."
            )

        return value

    def validate_ativo(self, value):
        ordem = self.instance

        # O ativo de uma ordem não muda depois da abertura (o histórico da
        # ordem passaria a falar de outro equipamento).
        if ordem is not None:
            if value.pk != ordem.ativo_id:
                raise serializers.ValidationError(
                    "O ativo de uma ordem não pode ser alterado."
                )
            return value

        if value.status == Ativo.Status.INATIVO:
            raise serializers.ValidationError(
                "Não é possível abrir ordem de manutenção para um ativo "
                "inativo."
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
