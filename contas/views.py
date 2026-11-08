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
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

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

    # -----------------------------------------------------------------------
    # REGRAS DE ADMINISTRAÇÃO
    # -----------------------------------------------------------------------

    def exigir_professor(self, mensagem):
        if not usuario_eh_professor(self.request.user):
            raise PermissionDenied(mensagem)

    def proteger_superusuario(self, alvo):
        """
        Superusuário só é administrado por outro superusuário.

        Sem isso, um professor poderia trocar a senha do superusuário e
        entrar no Django Admin com acesso total.
        """
        if alvo.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied(
                "Somente um superusuário pode administrar outro superusuário."
            )

    def registrar(self, tipo_evento, descricao, usuario):
        LogConta.objects.create(
            usuario=usuario,
            tipo_evento=tipo_evento,
            descricao=descricao,
            ip=obter_ip(self.request),
        )

    @staticmethod
    def encerrar_sessoes(usuario):
        """
        Invalida todos os refresh tokens do usuário (blacklist).
        O access token em uso expira sozinho no prazo configurado.
        """
        for token in OutstandingToken.objects.filter(user=usuario):
            BlacklistedToken.objects.get_or_create(token=token)

    # -----------------------------------------------------------------------
    # ATUALIZAR USUÁRIO
    # PUT /api/contas/usuarios/{id}/
    # PATCH /api/contas/usuarios/{id}/
    # -----------------------------------------------------------------------

    def update(self, request, *args, **kwargs):
        self.exigir_professor("Somente professores podem administrar usuários.")
        self.proteger_superusuario(self.get_object())

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self.exigir_professor("Somente professores podem administrar usuários.")
        self.proteger_superusuario(self.get_object())

        return super().partial_update(request, *args, **kwargs)

    @transaction.atomic
    def perform_update(self, serializer):
        alvo = serializer.instance
        dados = serializer.validated_data
        proprio = alvo.pk == self.request.user.pk

        perfil = getattr(alvo, "perfil", None)
        papel_antes = perfil.papel if perfil else Perfil.Papel.ALUNO
        ativo_antes = alvo.is_active

        papel_novo = dados.get("papel", papel_antes)
        ativo_novo = dados.get("is_active", ativo_antes)

        # Evita que alguém perca o próprio acesso por engano (e que o
        # sistema fique sem professor).
        if proprio and (papel_novo != papel_antes or ativo_novo != ativo_antes):
            raise PermissionDenied(
                "Você não pode alterar o próprio papel nem desativar a "
                "própria conta."
            )

        usuario = serializer.save()
        autor = self.request.user.username

        if papel_novo != papel_antes:
            self.registrar(
                LogConta.TipoEvento.PAPEL_ALTERADO,
                f"Papel de {usuario.username} alterado de {papel_antes} "
                f"para {papel_novo} por {autor}.",
                usuario,
            )

        if ativo_novo != ativo_antes:
            if not ativo_novo:
                # Conta desativada não deve continuar com sessões abertas.
                self.encerrar_sessoes(usuario)

            self.registrar(
                LogConta.TipoEvento.CONTA_REATIVADA
                if ativo_novo
                else LogConta.TipoEvento.CONTA_DESATIVADA,
                f"Conta de {usuario.username} "
                f"{'reativada' if ativo_novo else 'desativada'} por {autor}.",
                usuario,
            )

    # -----------------------------------------------------------------------
    # EXCLUIR USUÁRIO
    # DELETE /api/contas/usuarios/{id}/
    # -----------------------------------------------------------------------

    def destroy(self, request, *args, **kwargs):
        self.exigir_professor("Somente professores podem excluir usuários.")

        usuario = self.get_object()
        self.proteger_superusuario(usuario)

        if usuario.pk == request.user.pk:
            raise PermissionDenied(
                "Você não pode excluir sua própria conta por esta rota."
            )

        # O log fica com o autor, porque a conta excluída deixa de existir.
        self.registrar(
            LogConta.TipoEvento.USUARIO_EXCLUIDO,
            f"Usuário {usuario.username} excluído por {request.user.username}.",
            request.user,
        )

        return super().destroy(request, *args, **kwargs)

    # -----------------------------------------------------------------------
    # ALTERAR SENHA
    # PATCH /api/contas/usuarios/{id}/senha/
    # Corpo: {"password": "...", "senha_atual": "..."}
    # - Própria senha: exige a senha atual.
    # - Senha de outra pessoa: só professor (sem a senha atual).
    # Depois da troca, todas as sessões da conta são encerradas.
    # -----------------------------------------------------------------------

    @action(
        detail=True,
        methods=["patch"],
        url_path="senha",
        permission_classes=[IsAuthenticated],
    )
    def alterar_senha(self, request, pk=None):

        usuario = self.get_object()
        propria = usuario.pk == request.user.pk

        # Usuário comum só pode alterar a própria senha.
        if not propria and not usuario_eh_professor(request.user):
            raise PermissionDenied("Você só pode alterar a própria senha.")

        self.proteger_superusuario(usuario)

        def recusar(campo, mensagens):
            self.registrar(
                LogConta.TipoEvento.ALTERACAO_SENHA_FALHA,
                f"Troca de senha de {usuario.username} recusada ({campo}).",
                usuario,
            )
            return Response(
                {campo: mensagens},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if propria:
            senha_atual = request.data.get("senha_atual")

            if not isinstance(senha_atual, str) or not senha_atual:
                return recusar("senha_atual", ["Informe a senha atual."])

            if not usuario.check_password(senha_atual):
                return recusar("senha_atual", ["Senha atual incorreta."])

        nova_senha = request.data.get("password")

        if not isinstance(nova_senha, str) or not nova_senha:
            return recusar("password", ["A nova senha é obrigatória."])

        if usuario.check_password(nova_senha):
            return recusar(
                "password",
                ["A nova senha deve ser diferente da atual."],
            )

        try:
            validate_password(nova_senha, user=usuario)

        except ValidationError as exc:
            return recusar("password", list(exc.messages))

        with transaction.atomic():
            usuario.set_password(nova_senha)
            usuario.save(update_fields=["password"])

            self.encerrar_sessoes(usuario)

            self.registrar(
                LogConta.TipoEvento.SENHA_ALTERADA,
                (
                    "Senha alterada pelo próprio usuário."
                    if propria
                    else f"Senha redefinida por {request.user.username}."
                ),
                usuario,
            )

        return Response(
            {
                "detail": (
                    "Senha alterada com sucesso. As sessões abertas foram "
                    "encerradas; entre novamente com a nova senha."
                )
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

        # Cria uma nova consulta ao banco, sem reutilizar
        # o cache de resultados de um QuerySet já avaliado.
        queryset = self.queryset.all()

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
