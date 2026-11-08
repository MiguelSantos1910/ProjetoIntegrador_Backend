from datetime import timedelta
from math import ceil

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, Throttled

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Perfil, LogConta, TentativaLogin


# ---------------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------------------

def obter_ip(request):
    """
    Obtém o endereço IP da requisição.
    """
    if not request:
        return None

    return request.META.get("REMOTE_ADDR") or None


def usuario_eh_professor_ou_admin(user):
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


def registrar_log_conta(
    request,
    tipo_evento,
    descricao,
    usuario=None,
):
    """
    Centraliza o registro dos eventos de auditoria.
    """
    LogConta.objects.create(
        usuario=usuario,
        tipo_evento=tipo_evento,
        descricao=descricao,
        ip=obter_ip(request),
    )


# ---------------------------------------------------------------------------
# USUÁRIO AUTENTICADO
# ---------------------------------------------------------------------------

class MeSerializer(serializers.ModelSerializer):

    papel = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "papel",
        ]

    def get_papel(self, obj):
        perfil = Perfil.objects.filter(
            usuario=obj
        ).first()

        return perfil.papel if perfil else Perfil.Papel.ALUNO


# ---------------------------------------------------------------------------
# CONSULTA DE USUÁRIOS
# ---------------------------------------------------------------------------

class UsuarioSerializer(serializers.ModelSerializer):

    papel = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "papel",
        ]

    def get_papel(self, obj):
        perfil = Perfil.objects.filter(
            usuario=obj
        ).first()

        return perfil.papel if perfil else Perfil.Papel.ALUNO


# ---------------------------------------------------------------------------
# CADASTRO DE USUÁRIOS
# ---------------------------------------------------------------------------

class UsuarioCreateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )

    papel = serializers.ChoiceField(
        choices=Perfil.Papel.choices,
        required=False,
        default=Perfil.Papel.ALUNO,
    )

    class Meta:
        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "papel",
        ]

    def registrar_falha_validacao(self, erro):
        """
        Registra falhas de validação do cadastro.

        Não registra senhas nem outros dados sensíveis.
        """
        request = self.context.get("request")

        dados = getattr(self, "initial_data", {})

        username = str(
            dados.get("username", "")
        ).strip()

        usuario = User.objects.filter(
            username__iexact=username
        ).first() if username else None

        if isinstance(erro.detail, dict):
            campos = ", ".join(
                str(campo)
                for campo in erro.detail.keys()
            )
        else:
            campos = "dados do formulário"

        registrar_log_conta(
            request=request,
            tipo_evento=LogConta.TipoEvento.CADASTRO_FALHA,
            descricao=(
                "Cadastro recusado durante a validação. "
                f"Campos com erro: {campos}."
            ),
            usuario=usuario,
        )

    def run_validation(self, data):
        """
        Intercepta erros de validação para registrar a auditoria.
        """
        try:
            return super().run_validation(data)

        except serializers.ValidationError as erro:
            self.registrar_falha_validacao(erro)
            raise

    def validate_password(self, value):
        """
        Aplica as regras de segurança de senha configuradas no Django.
        """
        usuario = User(
            username=self.initial_data.get("username", ""),
            first_name=self.initial_data.get("first_name", ""),
            last_name=self.initial_data.get("last_name", ""),
            email=self.initial_data.get("email", ""),
        )

        try:
            validate_password(
                value,
                user=usuario,
            )

        except DjangoValidationError as erro:
            raise serializers.ValidationError(
                erro.messages
            )

        return value

    def validate(self, attrs):
        """
        Cadastro público permite somente o perfil ALUNO.
        """
        request = self.context.get("request")

        papel = attrs.get(
            "papel",
            Perfil.Papel.ALUNO,
        )

        if papel != Perfil.Papel.ALUNO:
            if not usuario_eh_professor_ou_admin(
                request.user if request else None
            ):
                raise serializers.ValidationError({
                    "papel": (
                        "Você não tem permissão para cadastrar "
                        "usuários com esse perfil."
                    )
                })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """
        Cria o usuário, seu perfil e registra o cadastro.
        """
        papel = validated_data.pop(
            "papel",
            Perfil.Papel.ALUNO,
        )

        password = validated_data.pop("password")

        usuario = User.objects.create_user(
            password=password,
            **validated_data,
        )

        Perfil.objects.update_or_create(
            usuario=usuario,
            defaults={
                "papel": papel,
            },
        )

        request = self.context.get("request")

        registrar_log_conta(
            request=request,
            tipo_evento=LogConta.TipoEvento.CADASTRO,
            descricao="Usuário cadastrado no sistema.",
            usuario=usuario,
        )

        return usuario


# ---------------------------------------------------------------------------
# ATUALIZAÇÃO DE USUÁRIOS
# ---------------------------------------------------------------------------

class UsuarioUpdateSerializer(serializers.ModelSerializer):

    papel = serializers.ChoiceField(
        choices=Perfil.Papel.choices,
        required=False,
    )

    class Meta:
        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "papel",
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        papel = validated_data.pop(
            "papel",
            None,
        )

        instance = super().update(
            instance,
            validated_data,
        )

        if papel is not None:
            perfil, _ = Perfil.objects.get_or_create(
                usuario=instance,
            )

            perfil.papel = papel

            perfil.save(
                update_fields=["papel"],
            )

        return instance


# ---------------------------------------------------------------------------
# LOGIN JWT COM LIMITAÇÃO DE TENTATIVAS E AUDITORIA
# ---------------------------------------------------------------------------

class LoginTokenSerializer(TokenObtainPairSerializer):
    """
    Autenticação JWT com limitação de tentativas.

    Regras:
    - Até cinco tentativas incorretas.
    - Bloqueio por 3 minutos após a quinta falha.
    - Identificação pela combinação de usuário e IP.
    - Reinicialização após login bem-sucedido.
    - Registro de todas as falhas relevantes.
    """

    LIMITE_TENTATIVAS = 5

    TEMPO_BLOQUEIO = timedelta(
        minutes=3
    )

    def obter_identificacao(self, attrs):
        """
        Obtém o usuário informado e o IP da requisição.
        """
        username = str(
            attrs.get(self.username_field, "")
        ).strip().casefold()

        request = self.context.get("request")

        ip = obter_ip(request) or ""

        return username, ip

    def obter_usuario(self, username):
        """
        Localiza o usuário para associar o log, quando existir.
        """
        return User.objects.filter(
            username__iexact=username
        ).first()

    def registrar_log(
        self,
        username,
        ip,
        tipo_evento,
        descricao,
    ):
        """
        Registra um evento de autenticação.
        """
        usuario = self.obter_usuario(username)

        LogConta.objects.create(
            usuario=usuario,
            tipo_evento=tipo_evento,
            descricao=descricao,
            ip=ip or None,
        )

    def verificar_bloqueio(self, username, ip):
        """
        Verifica se o usuário e IP possuem bloqueio ativo.
        """
        registro = TentativaLogin.objects.filter(
            username=username,
            ip=ip,
        ).first()

        if not registro or not registro.bloqueado_ate:
            return

        agora = timezone.now()

        if registro.bloqueado_ate > agora:
            segundos_restantes = ceil(
                (
                    registro.bloqueado_ate - agora
                ).total_seconds()
            )

            self.registrar_log(
                username,
                ip,
                LogConta.TipoEvento.LOGIN_BLOQUEADO,
                (
                    "Tentativa de login durante bloqueio ativo. "
                    f"Tempo restante: {segundos_restantes} segundos."
                ),
            )

            raise Throttled(
                wait=max(1, segundos_restantes),
                detail=(
                    "Muitas tentativas de login. "
                    "Aguarde o término do bloqueio de 3 minutos."
                ),
            )

    # Contadores sem atividade há mais tempo que isso são apagados.
    RETENCAO_TENTATIVAS = timedelta(days=1)

    def limpar_tentativas_antigas(self):
        """
        Remove contadores antigos sem bloqueio ativo.

        Tentativas com usuários inexistentes também criam contador (assim a
        resposta é igual para usuário existente ou não, sem revelar quais
        contas existem); a limpeza evita que a tabela cresça sem limite.
        """
        limite = timezone.now() - self.RETENCAO_TENTATIVAS

        TentativaLogin.objects.filter(
            atualizado_em__lt=limite,
        ).exclude(
            bloqueado_ate__gt=timezone.now(),
        ).delete()

    def registrar_falha(self, username, ip):
        """
        Registra uma tentativa incorreta.

        A quinta tentativa inicia o bloqueio de 3 minutos.
        """
        espera = None

        self.limpar_tentativas_antigas()

        with transaction.atomic():

            registro, _ = TentativaLogin.objects.get_or_create(
                username=username,
                ip=ip,
            )

            registro = TentativaLogin.objects.select_for_update().get(
                pk=registro.pk
            )

            agora = timezone.now()

            # Proteção contra tentativas concorrentes.
            if (
                registro.bloqueado_ate
                and registro.bloqueado_ate > agora
            ):
                espera = ceil(
                    (
                        registro.bloqueado_ate - agora
                    ).total_seconds()
                )

                self.registrar_log(
                    username,
                    ip,
                    LogConta.TipoEvento.LOGIN_BLOQUEADO,
                    "Tentativa de login durante bloqueio ativo.",
                )

            else:

                # Reinicia o contador se o bloqueio anterior expirou.
                if (
                    registro.bloqueado_ate
                    and registro.bloqueado_ate <= agora
                ):
                    registro.tentativas = 0
                    registro.bloqueado_ate = None

                registro.tentativas += 1

                # Salva o bloqueio ao atingir cinco tentativas.
                if registro.tentativas >= self.LIMITE_TENTATIVAS:
                    registro.bloqueado_ate = (
                        agora + self.TEMPO_BLOQUEIO
                    )

                    espera = ceil(
                        self.TEMPO_BLOQUEIO.total_seconds()
                    )

                registro.save(
                    update_fields=[
                        "tentativas",
                        "bloqueado_ate",
                        "atualizado_em",
                    ]
                )

                # Registra a falha de autenticação.
                self.registrar_log(
                    username,
                    ip,
                    LogConta.TipoEvento.LOGIN_FALHA,
                    (
                        "Falha na autenticação. "
                        f"Tentativa {registro.tentativas} "
                        f"de {self.LIMITE_TENTATIVAS}."
                    ),
                )

                # Registra também o início do bloqueio.
                if registro.tentativas >= self.LIMITE_TENTATIVAS:
                    self.registrar_log(
                        username,
                        ip,
                        LogConta.TipoEvento.LOGIN_BLOQUEADO,
                        (
                            "Limite de cinco tentativas atingido. "
                            "Acesso bloqueado por 3 minutos."
                        ),
                    )

        # Lança a exceção somente depois de salvar a transação.
        if espera is not None:
            raise Throttled(
                wait=max(1, espera),
                detail=(
                    "Limite de tentativas atingido. "
                    "Seu acesso foi bloqueado por 3 minutos."
                ),
            )

    def reiniciar_tentativas(self, username, ip):
        """
        Remove o contador após autenticação bem-sucedida.
        """
        TentativaLogin.objects.filter(
            username=username,
            ip=ip,
        ).delete()

    def validate(self, attrs):
        """
        Executa a autenticação com controle de tentativas.
        """
        username, ip = self.obter_identificacao(attrs)

        # 1. Verifica se existe bloqueio ativo.
        self.verificar_bloqueio(username, ip)

        try:
            # 2. Executa a autenticação JWT original.
            dados = super().validate(attrs)

        except AuthenticationFailed:
            # 3. Registra a falha.
            # A quinta tentativa poderá gerar HTTP 429.
            self.registrar_falha(username, ip)
            raise

        # 4. Login bem-sucedido.
        with transaction.atomic():

            self.reiniciar_tentativas(
                username,
                ip,
            )

            self.registrar_log(
                username,
                ip,
                LogConta.TipoEvento.LOGIN,
                "Login realizado com sucesso.",
            )

        return dados


# ---------------------------------------------------------------------------
# AUDITORIA DE CONTAS
# ---------------------------------------------------------------------------

class LogContaSerializer(serializers.ModelSerializer):

    usuario_nome = serializers.SerializerMethodField()

    tipo_evento_display = serializers.CharField(
        source="get_tipo_evento_display",
        read_only=True,
    )

    class Meta:
        model = LogConta

        fields = [
            "id",
            "usuario",
            "usuario_nome",
            "tipo_evento",
            "tipo_evento_display",
            "descricao",
            "ip",
            "data",
        ]

        read_only_fields = fields

    def get_usuario_nome(self, obj):
        if obj.usuario:
            return obj.usuario.username

        # Sem usuário: login com usuário inexistente, comando de terminal
        # ou conta excluída depois do evento.
        return "Não identificado"
