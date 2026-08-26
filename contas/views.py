from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import MeSerializer


class MeView(APIView):
    """
    GET /api/contas/me/  -> dados do usuário autenticado + papel (professor/aluno/suporte).
    O app mobile e o painel web chamam isso logo após o login (via JWT) para
    saber qual papel o usuário tem e ajustar o que mostrar na tela.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)
