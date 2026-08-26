from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Perfil


class MeSerializer(serializers.ModelSerializer):
    papel = serializers.CharField(source="perfil.papel", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "papel"]
