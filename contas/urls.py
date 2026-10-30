
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MeView,
    UsuarioViewSet,
    LogoutView,
    LogContaViewSet,
)

router = DefaultRouter()

# CRUD de usuários
router.register(
    "usuarios",
    UsuarioViewSet,
    basename="usuarios",
)

# Consulta dos logs de contas
router.register(
    "logs",
    LogContaViewSet,
    basename="logs-contas",
)

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

    # Rotas do CRUD e dos logs
    path(
        "",
        include(router.urls),
    ),
]
