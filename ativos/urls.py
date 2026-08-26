from rest_framework.routers import DefaultRouter

from .views import AtivoViewSet, HistoricoMovimentacaoViewSet

router = DefaultRouter()
router.register("ativos", AtivoViewSet, basename="ativo")
router.register("historico", HistoricoMovimentacaoViewSet, basename="historico")

urlpatterns = router.urls
