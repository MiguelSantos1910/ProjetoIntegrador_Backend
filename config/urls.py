from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from contas.views import LoginView


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/health/", health, name="health"),

    # Login personalizado: registra o evento LOGIN
    path("api/token/", LoginView.as_view(), name="token_obtain_pair"),

    # Renovação do token
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Contas e auditoria
    path("api/contas/", include("contas.urls")),

    # Ativos e manutenção
    path("api/", include("ativos.urls")),
    path("api/", include("ordens_manutencao.urls")),
]