from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Perfil


class MeSerializer(serializers.ModelSerializer):
    papel = serializers.CharField(
        source="perfil.papel",
        read_only=True
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
        read_only=True
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
        required=True
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")

        usuario = User.objects.create_user(
            password=password,
            **validated_data
        )

        return usuario


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    papel = serializers.ChoiceField(
        choices=Perfil.Papel.choices,
        required=False
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

    def update(self, instance, validated_data):
        papel = validated_data.pop("papel", None)

        instance = super().update(
            instance,
            validated_data
        )

        if papel is not None:
            perfil, _ = Perfil.objects.get_or_create(
                usuario=instance
            )

            perfil.papel = papel
            perfil.save()

        return instance