from rest_framework import viewsets
from .models import OrdemManutencao
from .serializers import OrdemManutencaoSerializer

class OrdemManutencaoViewSet(viewsets.ModelViewSet):
    queryset = OrdemManutencao.objects.select_related('ativo').all()
    serializer_class = OrdemManutencaoSerializer

