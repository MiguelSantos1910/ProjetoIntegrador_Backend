
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Perfil
from .serializers import (
    UsuarioCreateSerializer,
    UsuarioSerializer,
    UsuarioUpdateSerializer,
    MeSerializer,
)


def usuario_eh_professor(user):
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    perfil = getattr(user, "perfil", None)
    return getattr(perfil, "papel", None) == Perfil.Papel.PROFESSOR


class MeView(APIView):
    """
    GET /api/contas/me/
    Retorna os dados do usuário autenticado e seu papel.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("perfil").all().order_by("username")
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]

        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCreateSerializer

        if self.action in ["update", "partial_update"]:
            return UsuarioUpdateSerializer

        return UsuarioSerializer

    def get_queryset(self):
        user = self.request.user

        # Apenas professor pode listar e administrar todas as contas.
        if usuario_eh_professor(user):
            return self.queryset

        # Usuários comuns só podem consultar a própria conta.
        return self.queryset.filter(pk=user.pk)

    def update(self, request, *args, **kwargs):
        if not usuario_eh_professor(request.user):
            raise PermissionDenied(
                "Somente professores autorizados podem administrar usuários."
            )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not usuario_eh_professor(request.user):
            raise PermissionDenied(
                "Somente professores autorizados podem administrar usuários."
            )

        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not usuario_eh_professor(request.user):
            raise PermissionDenied(
                "Somente professores autorizados podem excluir usuários."
            )

        usuario = self.get_object()

        if usuario.pk == request.user.pk:
            raise PermissionDenied(
                "Você não pode excluir sua própria conta por esta rota."
            )

        return super().destroy(request, *args, **kwargs)

    @action(
        detail=True,
        methods=["patch"],
        url_path="senha",
        permission_classes=[IsAuthenticated],
    )
    def alterar_senha(self, request, pk=None):
        usuario = self.get_object()

        # Usuário comum só pode alterar a própria senha.
        if (
            usuario.pk != request.user.pk
            and not usuario_eh_professor(request.user)
        ):
            raise PermissionDenied(
                "Você só pode alterar a própria senha."
            )

        nova_senha = request.data.get("password")

        if not nova_senha:
            return Response(
                {"detail": "A nova senha é obrigatória."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(nova_senha, user=usuario)
        except Exception as exc:
            from django.core.exceptions import ValidationError

            if isinstance(exc, ValidationError):
                return Response(
                    {"password": list(exc.messages)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            raise

        usuario.set_password(nova_senha)
        usuario.save(update_fields=["password"])

        return Response(
            {"detail": "Senha alterada com sucesso."},
            status=status.HTTP_200_OK,
        )
