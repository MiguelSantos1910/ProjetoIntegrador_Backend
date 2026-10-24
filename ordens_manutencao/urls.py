
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import OrdemManutencaoViewSet, listar_logs_ordem

router = DefaultRouter()

router.register(
    r'ordens_manutencao',
    OrdemManutencaoViewSet,
    basename='ordens_manutencao',
)

urlpatterns = [
    *router.urls,
    path(
        'ordens_manutencao/<int:ordem_id>/logs/',
        listar_logs_ordem,
        name='logs_ordem_manutencao',
    ),
]
