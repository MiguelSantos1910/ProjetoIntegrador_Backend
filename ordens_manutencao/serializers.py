from rest_framework import serializers
from .models import OrdemManutencao

class OrdemManutencaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdemManutencao
        fields = '__all__'
        read_only_fields = ['id', 'data_abertura', 'data_conclusao']