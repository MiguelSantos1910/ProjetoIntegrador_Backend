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


class HistoricoMudancaStatusTestCase(APITestCase):
    """Eventos gravados no histórico quando o status do ativo muda (B12)."""

    def setUp(self):
        self.professor = User.objects.create_user(username="professor_hist", password="senha-teste-123")
        self.professor.perfil.papel = "PROFESSOR"
        self.professor.perfil.save()
        self.client.force_authenticate(self.professor)

    def mudar_status(self, status_inicial, status_novo):
        ativo = Ativo.objects.create(
            tipo="MONITOR", descricao="MONITOR TESTE", sala="B-111", status=status_inicial
        )
        resposta = self.client.patch(f"/api/ativos/{ativo.id}/", {"status": status_novo})
        self.assertEqual(resposta.status_code, 200, resposta.data)
        return ativo.historico.first()

    def test_eventos_por_transicao(self):
        casos = [
            ("ATIVO", "EM_MANUTENCAO", "MANUTENCAO"),
            ("ATIVO", "DEVOLVIDO", "DEVOLUCAO"),
            ("ATIVO", "INATIVO", "INATIVO"),
            # Saindo de Inativo: sempre reativação
            ("INATIVO", "ATIVO", "REATIVACAO"),
            ("INATIVO", "EM_MANUTENCAO", "REATIVACAO"),
            ("INATIVO", "DEVOLVIDO", "REATIVACAO"),
            # Voltando a Ativo depois de manutenção ou devolução
            ("EM_MANUTENCAO", "ATIVO", "RETORNO"),
            ("DEVOLVIDO", "ATIVO", "RETORNO"),
        ]

        for status_inicial, status_novo, evento_esperado in casos:
            with self.subTest(de=status_inicial, para=status_novo):
                evento = self.mudar_status(status_inicial, status_novo)

                self.assertIsNotNone(evento)
                self.assertEqual(evento.tipo_evento, evento_esperado)
                self.assertEqual(evento.usuario, self.professor)

    def test_reativacao_informa_o_novo_status(self):
        evento = self.mudar_status("INATIVO", "EM_MANUTENCAO")

        self.assertEqual(evento.descricao, "Status alterado de Inativo para Em manutenção.")

    def test_sem_mudanca_de_status_nao_gera_evento(self):
        ativo = Ativo.objects.create(tipo="MESA", descricao="MESA", sala="B-111", status="ATIVO")

        self.client.patch(f"/api/ativos/{ativo.id}/", {"descricao": "MESA NOVA"})

        self.assertEqual(ativo.historico.count(), 0)
