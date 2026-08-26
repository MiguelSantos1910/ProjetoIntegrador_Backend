from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import Ativo


class AtivoAPITestCase(APITestCase):
    """
    Ponto de partida para o plano de testes do Guilherme (G2.1/G2.3).
    Rode com: python manage.py test
    """

    def setUp(self):
        self.professor = User.objects.create_user(username="eduardo", password="senha-teste-123")
        self.professor.perfil.papel = "PROFESSOR"
        self.professor.perfil.save()

    def test_listar_ativos_exige_autenticacao(self):
        resp = self.client.get("/api/ativos/")
        self.assertEqual(resp.status_code, 401)

    def test_professor_cadastra_ativo(self):
        self.client.force_authenticate(self.professor)
        resp = self.client.post(
            "/api/ativos/",
            {"tipo": "GABINETE", "descricao": "WORKSTATION CORPORATIVO", "sala": "B-111"},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Ativo.objects.count(), 1)
        # o cadastro deve gerar automaticamente uma entrada no histórico
        self.assertEqual(Ativo.objects.first().historico.count(), 1)
