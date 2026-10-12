from rest_framework.routers import DefaultRouter
from .views import OrdemManutencaoViewSet

router = DefaultRouter()
router.register(
    r'ordens_manutencao',
    OrdemManutencaoViewSet,
    basename='ordens_manutencao'
)

urlpatterns = router.urls