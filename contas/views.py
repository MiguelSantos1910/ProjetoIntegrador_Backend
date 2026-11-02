from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
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


# ---------------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------------------

def usuario_eh_professor(user):
    """
    Verifica se o usuário é professor ou superusuário.
    """

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return Perfil.objects.filter(
        usuario=user,
        papel=Perfil.Papel.PROFESSOR,
    ).exists()


def obter_ip(request):
    """
    Obtém o endereço IP da requisição.
    """

    if not request:
        return None

    return request.META.get("REMOTE_ADDR") or None


# ---------------------------------------------------------------------------
# LOGIN
# POST /api/token/
# ---------------------------------------------------------------------------

class LoginView(TokenObtainPairView):
    """
    Autentica o usuário utilizando JWT.

    O LoginTokenSerializer é responsável por:
    - Controlar as tentativas de login.
    - Bloquear após cinco tentativas incorretas.
    - Aplicar bloqueio de 3 minutos.
    - Registrar login bem-sucedido.
    - Registrar falhas e bloqueios na auditoria.
    """

    serializer_class = LoginTokenSerializer


# ---------------------------------------------------------------------------
# LOGOUT
# POST /api/contas/logout/
# ---------------------------------------------------------------------------

class LogoutView(APIView):
    """
    Invalida o refresh token e registra o evento LOGOUT.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        refresh_token = request.data.get("refresh")

        if not refresh_token or not isinstance(refresh_token, str):
            return Response(
                {
                    "detail": "O refresh token é obrigatório."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)

            # Verifica se o token pertence ao usuário autenticado.
            token_user_id = token.get("user_id")

            if str(token_user_id) != str(request.user.pk):
                return Response(
                    {
                        "detail": (
                            "O token informado não pertence "
                            "ao usuário autenticado."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Invalida o refresh token.
            token.blacklist()

            # Registra o logout somente após invalidar o token.
            LogConta.objects.create(
                usuario=request.user,
                tipo_evento=LogConta.TipoEvento.LOGOUT,
                descricao="Logout realizado com sucesso.",
                ip=obter_ip(request),
            )

            return Response(
                {
                    "detail": "Logout realizado com sucesso."
                },
                status=status.HTTP_200_OK,
            )

        except TokenError:
            return Response(
                {
                    "detail": "Refresh token inválido ou expirado."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


# ---------------------------------------------------------------------------
# USUÁRIO AUTENTICADO
# GET /api/contas/me/
# ---------------------------------------------------------------------------

class MeView(APIView):
    """
    Retorna os dados do usuário autenticado.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):

        serializer = MeSerializer(request.user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# GERENCIAMENTO DE USUÁRIOS
# ---------------------------------------------------------------------------

class UsuarioViewSet(viewsets.ModelViewSet):
    """
    Gerenciamento de usuários.

    Permissões:
    - Cadastro: público, com perfil ALUNO por padrão.
    - Consulta: usuário autenticado.
    - Consulta de todos os usuários: professor ou superusuário.
    - Edição: professor ou superusuário.
    - Exclusão: professor ou superusuário.
    - Alteração de senha: próprio usuário ou professor.
    """

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

    # -----------------------------------------------------------------------
    # ATUALIZAR USUÁRIO
    # PUT /api/contas/usuarios/{id}/
    # PATCH /api/contas/usuarios/{id}/
    # -----------------------------------------------------------------------

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

    # -----------------------------------------------------------------------
    # EXCLUIR USUÁRIO
    # DELETE /api/contas/usuarios/{id}/
    # -----------------------------------------------------------------------

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

    # -----------------------------------------------------------------------
    # ALTERAR SENHA
    # PATCH /api/contas/usuarios/{id}/senha/
    # -----------------------------------------------------------------------

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

        if not isinstance(nova_senha, str) or not nova_senha:
            return Response(
                {
                    "password": "A nova senha é obrigatória."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(
                nova_senha,
                user=usuario,
            )

        except ValidationError as exc:
            return Response(
                {
                    "password": list(exc.messages)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():

            usuario.set_password(nova_senha)

            usuario.save(
                update_fields=["password"]
            )

        return Response(
            {
                "detail": "Senha alterada com sucesso."
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# AUDITORIA DE CONTAS
# GET /api/contas/auditoria/
# ---------------------------------------------------------------------------

class LogContaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Consulta os registros de auditoria das contas.

    Eventos registrados:
    - CADASTRO
    - CADASTRO_FALHA
    - LOGIN
    - LOGIN_FALHA
    - LOGIN_BLOQUEADO
    - LOGOUT

    Somente professores e superusuários podem consultar.
    """

    queryset = LogConta.objects.select_related(
        "usuario"
    ).all().order_by("-data")

    serializer_class = LogContaSerializer

    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        if not usuario_eh_professor(self.request.user):
            raise PermissionDenied(
                "Somente professores podem consultar "
                "os logs das contas."
            )

        queryset = self.queryset

        # ---------------------------------------------------------------
        # FILTRO POR USUÁRIO
        # Exemplo: /api/contas/auditoria/?usuario=2
        # ---------------------------------------------------------------

        usuario_id = self.request.query_params.get("usuario")

        if usuario_id:

            if not usuario_id.isdigit():
                raise DRFValidationError({
                    "usuario": "Informe um ID de usuário válido."
                })

            queryset = queryset.filter(
                usuario_id=usuario_id
            )

        # ---------------------------------------------------------------
        # FILTRO POR TIPO DE EVENTO
        # Exemplo: /api/contas/auditoria/?tipo_evento=LOGIN_FALHA
        # ---------------------------------------------------------------

        tipo_evento = self.request.query_params.get("tipo_evento")

        if tipo_evento:

            tipos_validos = {
                escolha[0]
                for escolha in LogConta.TipoEvento.choices
            }

            if tipo_evento not in tipos_validos:
                raise DRFValidationError({
                    "tipo_evento": (
                        "Tipo de evento inválido. "
                        f"Valores permitidos: {', '.join(sorted(tipos_validos))}."
                    )
                })

            queryset = queryset.filter(
                tipo_evento=tipo_evento
            )

        return queryset
