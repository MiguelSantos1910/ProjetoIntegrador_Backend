from django.contrib.auth.models import User

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    UsuarioCreateSerializer,
    UsuarioSerializer,
    UsuarioUpdateSerializer,
    MeSerializer
)


class MeView(APIView):
    """
    GET /api/contas/me/
    Retorna os dados do usuário autenticado + papel.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            MeSerializer(request.user).data
        )


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("username")
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

    @action(
        detail = True,
        methods = ["patch"],
        url_path = "senha"
    )
    def alterar_senha(self, request, pk=None):
        usuario = self.get_object()

        nova_senha = request.data.get("password")

        if not nova_senha:
            return Response(
                {
                    "detail": "A nova senha é obrigatória."
                },
                status = status.HTTP_400_BAD_REQUEST
            )

        usuario.set_password(nova_senha)
        usuario.save()

        return Response(
            {
                "detail": "Senha alterada com sucesso."
            },
            status = status.HTTP_200_OK
        )