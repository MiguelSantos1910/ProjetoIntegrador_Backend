from rest_framework import serializers
from .models import OrdemManutencao, LogOrdemManutencao


class OrdemManutencaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdemManutencao
        fields = '__all__'
        read_only_fields = [
            'id',
            'data_abertura',
            'data_conclusao',
        ]


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
        read_only_fields = fields
