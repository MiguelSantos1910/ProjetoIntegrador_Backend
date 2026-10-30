
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import Perfil, LogConta

from .serializers import (
    UsuarioCreateSerializer,
    UsuarioSerializer,
    UsuarioUpdateSerializer,
    MeSerializer,
    LoginTokenSerializer,
    LogContaSerializer,
)


def usuario_eh_professor(user):
    """
    Verifica se o usuário é professor ou superusuário.
    """

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    perfil = getattr(user, "perfil", None)

    return getattr(perfil, "papel", None) == Perfil.Papel.PROFESSOR


class LoginView(TokenObtainPairView):
    """
    POST /api/token/

    Autentica o usuário e registra o login.
    """

    serializer_class = LoginTokenSerializer


class LogoutView(APIView):
    """
    POST /api/contas/logout/

    Invalida o refresh token e registra o logout.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "O refresh token é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)

            # Impede que um usuário invalide o token de outra conta.
            if str(token.get("user_id")) != str(request.user.pk):
                return Response(
                    {"detail": "O token informado não pertence ao usuário autenticado."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            token.blacklist()

            LogConta.objects.create(
                usuario=request.user,
                tipo_evento=LogConta.TipoEvento.LOGOUT,
                descricao="Logout realizado com sucesso.",
                ip=request.META.get("REMOTE_ADDR"),
            )

            return Response(
                {"detail": "Logout realizado com sucesso."},
                status=status.HTTP_200_OK,
            )

        except TokenError:
            return Response(
                {"detail": "Refresh token inválido ou expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class MeView(APIView):
    """
    GET /api/contas/me/

    Retorna os dados do usuário autenticado.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            MeSerializer(request.user).data
        )


class UsuarioViewSet(viewsets.ModelViewSet):

    queryset = User.objects.select_related(
        "perfil"
    ).all().order_by("username")

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

        if usuario_eh_professor(user):
            return self.queryset

        return self.queryset.filter(
            pk=user.pk
        )

    def update(self, request, *args, **kwargs):

        if not usuario_eh_professor(request.user):
            raise PermissionDenied(
                "Somente professores podem administrar usuários."
            )

        return super().update(
            request,
            *args,
            **kwargs,
        )

    def partial_update(self, request, *args, **kwargs):

        if not usuario_eh_professor(request.user):
            raise PermissionDenied(
                "Somente professores podem administrar usuários."
            )

        return super().partial_update(
            request,
            *args,
            **kwargs,
        )

    def destroy(self, request, *args, **kwargs):

        if not usuario_eh_professor(request.user):
            raise PermissionDenied(
                "Somente professores podem excluir usuários."
            )

        usuario = self.get_object()

        if usuario.pk == request.user.pk:
            raise PermissionDenied(
                "Você não pode excluir sua própria conta por esta rota."
            )

        return super().destroy(
            request,
            *args,
            **kwargs,
        )

    @action(
        detail=True,
        methods=["patch"],
        url_path="senha",
        permission_classes=[IsAuthenticated],
    )
    def alterar_senha(self, request, pk=None):

        usuario = self.get_object()

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
            validate_password(
                nova_senha,
                user=usuario,
            )

        except ValidationError as exc:
            return Response(
                {"password": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        usuario.set_password(nova_senha)

        usuario.save(
            update_fields=["password"]
        )

        return Response(
            {"detail": "Senha alterada com sucesso."},
            status=status.HTTP_200_OK,
        )


class LogContaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Consulta os logs de cadastro, login e logout.

    A consulta é permitida somente para professores
    e superusuários.
    """

    queryset = LogConta.objects.select_related(
        "usuario"
    ).all()

    serializer_class = LogContaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        if not usuario_eh_professor(self.request.user):
            raise PermissionDenied(
                "Somente professores podem consultar os logs das contas."
            )

        queryset = self.queryset

        usuario_id = self.request.query_params.get("usuario")
        tipo_evento = self.request.query_params.get("tipo_evento")

        if usuario_id:
            queryset = queryset.filter(
                usuario_id=usuario_id
            )

        if tipo_evento:
            queryset = queryset.filter(
                tipo_evento=tipo_evento
            )

        return queryset
