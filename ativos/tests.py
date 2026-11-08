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


class PermissoesAtivosTestCase(APITestCase):
    """Casos de mau uso: aluno alterando ativos, exclusão e histórico editável."""

    def setUp(self):
        self.aluno = User.objects.create_user(username="aluno_ativos", password="senha-teste-123")
        self.professor = User.objects.create_user(username="prof_ativos", password="senha-teste-123")
        self.professor.perfil.papel = "PROFESSOR"
        self.professor.perfil.save()
        self.ativo = Ativo.objects.create(tipo="MESA", descricao="MESA PERM", sala="B-111")

    def test_aluno_consulta_mas_nao_altera(self):
        self.client.force_authenticate(self.aluno)

        self.assertEqual(self.client.get("/api/ativos/").status_code, 200)
        self.assertEqual(
            self.client.post("/api/ativos/", {"tipo": "MESA", "descricao": "X", "sala": "B-111"}).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(f"/api/ativos/{self.ativo.id}/", {"sala": "OUTRA"}).status_code, 403
        )
        self.ativo.refresh_from_db()
        self.assertEqual(self.ativo.sala, "B-111")

    def test_ativo_nao_pode_ser_excluido(self):
        self.client.force_authenticate(self.professor)

        self.assertEqual(self.client.delete(f"/api/ativos/{self.ativo.id}/").status_code, 403)
        self.assertTrue(Ativo.objects.filter(pk=self.ativo.id).exists())

    def test_historico_nao_pode_ser_criado_editado_ou_apagado(self):
        self.client.force_authenticate(self.professor)
        self.client.patch(f"/api/ativos/{self.ativo.id}/", {"status": "INATIVO"})
        evento = self.ativo.historico.first()

        self.assertEqual(
            self.client.post("/api/historico/", {"ativo": self.ativo.id, "tipo_evento": "ENTREGA"}).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(f"/api/historico/{evento.id}/", {"descricao": "x"}).status_code, 403
        )
        self.assertEqual(self.client.delete(f"/api/historico/{evento.id}/").status_code, 403)
        self.assertTrue(self.ativo.historico.filter(pk=evento.id).exists())

    def test_busca_pelo_codigo_qr(self):
        self.client.force_authenticate(self.aluno)

        resposta = self.client.get(f"/api/ativos/?codigo_qr={self.ativo.codigo_qr}")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([a["id"] for a in resposta.data], [self.ativo.id])


class AtivoRevisaoBackTestCase(APITestCase):
    """Regressões da revisão do back (itens 1, 6 e 8)."""

    def setUp(self):
        self.professor = User.objects.create_user(username="prof_rev", password="senha-teste-123")
        self.professor.perfil.papel = "PROFESSOR"
        self.professor.perfil.save()
        self.client.force_authenticate(self.professor)

    def cadastrar(self, **extra):
        dados = {"tipo": "TECLADO", "descricao": "TECLADO", "sala": "B-111", **extra}
        return self.client.post("/api/ativos/", dados, format="json")

    def test_varios_ativos_sem_patrimonio(self):
        primeiro = self.cadastrar(numero_patrimonio="")
        segundo = self.cadastrar(numero_patrimonio="  ")
        terceiro = self.cadastrar()

        for resposta in (primeiro, segundo, terceiro):
            self.assertEqual(resposta.status_code, 201, resposta.data)
            self.assertIsNone(resposta.data["numero_patrimonio"])

    def test_patrimonio_repetido_recusado_com_400(self):
        self.cadastrar(numero_patrimonio="PAT-1")

        self.assertEqual(self.cadastrar(numero_patrimonio="PAT-1").status_code, 400)

    def test_mudanca_de_sala_gera_evento(self):
        ativo = Ativo.objects.create(tipo="MESA", descricao="MESA", sala="B-111")

        self.client.patch(f"/api/ativos/{ativo.id}/", {"sala": "B-112"}, format="json")

        evento = ativo.historico.get(tipo_evento="MUDANCA_SALA")
        self.assertIn("B-112", evento.descricao)

    def test_coordenadas_fora_do_intervalo(self):
        self.assertEqual(self.cadastrar(latitude="500").status_code, 400)
        self.assertEqual(self.cadastrar(longitude="-181").status_code, 400)
        self.assertEqual(
            self.cadastrar(latitude="-23.550520", longitude="-46.633308").status_code, 201
        )
