from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Perfil, LogConta


def obter_ip(request):
    """
    Obtém o endereço IP da requisição.
    """

    if not request:
        return None

    return request.META.get("REMOTE_ADDR")


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


class MeSerializer(serializers.ModelSerializer):

    papel = serializers.CharField(
        source="perfil.papel",
        read_only=True,
    )

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


class UsuarioSerializer(serializers.ModelSerializer):

    papel = serializers.CharField(
        source="perfil.papel",
        read_only=True,
    )

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


class UsuarioCreateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=True,
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

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):

        request = self.context.get("request")

        papel = attrs.get(
            "papel",
            Perfil.Papel.ALUNO,
        )

        # Cadastro público: somente ALUNO.
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

        LogConta.objects.create(
            usuario=usuario,
            tipo_evento=LogConta.TipoEvento.CADASTRO,
            descricao="Usuário cadastrado no sistema.",
            ip=obter_ip(request),
        )

        return usuario


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

        papel = validated_data.pop("papel", None)

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


class LoginTokenSerializer(TokenObtainPairSerializer):
    """
    Registra o login somente após a autenticação bem-sucedida.
    """

    def validate(self, attrs):

        dados = super().validate(attrs)

        request = self.context.get("request")

        LogConta.objects.create(
            usuario=self.user,
            tipo_evento=LogConta.TipoEvento.LOGIN,
            descricao="Login realizado com sucesso.",
            ip=obter_ip(request),
        )

        return dados


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

        return "Usuário removido"
