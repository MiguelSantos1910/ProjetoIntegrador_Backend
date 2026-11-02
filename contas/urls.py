from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MeView,
    UsuarioViewSet,
    LogoutView,
    LogContaViewSet,
)


# ---------------------------------------------------------------------------
# ROUTER
# ---------------------------------------------------------------------------

router = DefaultRouter()

# CRUD de usuários
router.register(
    "usuarios",
    UsuarioViewSet,
    basename="usuarios",
)

# Consulta dos logs de auditoria das contas
router.register(
    "auditoria",
    LogContaViewSet,
    basename="auditoria-contas",
)


# ---------------------------------------------------------------------------
# URLS
# ---------------------------------------------------------------------------

urlpatterns = [

    # Dados do usuário autenticado
    path(
        "me/",
        MeView.as_view(),
        name="me",
    ),

    # Encerramento da sessão
    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),

    # Rotas do CRUD de usuários e auditoria
    path(
        "",
        include(router.urls),
    ),
]
