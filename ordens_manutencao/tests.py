"""
Testes de ordens de manutenção: permissões por papel, rastreabilidade
(sem exclusão, logs somente leitura) e registro das mudanças de status.
Rode com: python manage.py test ordens_manutencao
"""

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from ativos.models import Ativo

from .models import LogOrdemManutencao, OrdemManutencao


URL = "/api/ordens_manutencao/"


def criar_usuario(username, papel):
    usuario = User.objects.create_user(username=username, password="Senha-teste-123")
    usuario.perfil.papel = papel
    usuario.perfil.save()
    return usuario


class OrdemManutencaoTestCase(APITestCase):

    def setUp(self):
        self.aluno = criar_usuario("aluno_os", "ALUNO")
        self.suporte = criar_usuario("suporte_os", "SUPORTE")
        self.professor = criar_usuario("professor_os", "PROFESSOR")
        self.ativo = Ativo.objects.create(tipo="GABINETE", descricao="GABINETE OS", sala="B-111")

    def dados_ordem(self):
        return {
            "ativo": self.ativo.id,
            "descricao": "Troca da fonte",
            "responsavel": "Equipe de suporte",
        }

    def criar_ordem(self, usuario):
        self.client.force_authenticate(usuario)
        return self.client.post(URL, self.dados_ordem(), format="json")

    def test_aluno_nao_abre_ordem(self):
        resposta = self.criar_ordem(self.aluno)

        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(OrdemManutencao.objects.count(), 0)

    def test_aluno_consulta_ordens(self):
        self.client.force_authenticate(self.aluno)

        self.assertEqual(self.client.get(URL).status_code, 200)

    def test_suporte_e_professor_abrem_ordem_com_log(self):
        for usuario in (self.suporte, self.professor):
            resposta = self.criar_ordem(usuario)
            self.assertEqual(resposta.status_code, 201, resposta.data)

        self.assertEqual(OrdemManutencao.objects.count(), 2)
        self.assertEqual(LogOrdemManutencao.objects.filter(acao="Criada").count(), 2)

    def test_mudanca_de_status_gera_log_e_data_de_conclusao(self):
        ordem_id = self.criar_ordem(self.suporte).data["id"]

        resposta = self.client.patch(f"{URL}{ordem_id}/", {"status": "Concluída"}, format="json")

        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertIsNotNone(resposta.data["data_conclusao"])
        log = LogOrdemManutencao.objects.filter(ordem_id=ordem_id, acao="Status alterado").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status_novo, "Concluída")

    def test_cancelar_ordem_mantem_o_registro(self):
        ordem_id = self.criar_ordem(self.suporte).data["id"]

        resposta = self.client.patch(f"{URL}{ordem_id}/", {"status": "Cancelada"}, format="json")

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(OrdemManutencao.objects.filter(pk=ordem_id, status="Cancelada").exists())

    def test_status_invalido_recusado(self):
        ordem_id = self.criar_ordem(self.suporte).data["id"]

        resposta = self.client.patch(f"{URL}{ordem_id}/", {"status": "Qualquer"}, format="json")

        self.assertEqual(resposta.status_code, 400)

    def test_ninguem_exclui_ordem(self):
        ordem_id = self.criar_ordem(self.suporte).data["id"]

        for usuario in (self.suporte, self.professor):
            self.client.force_authenticate(usuario)
            self.assertEqual(self.client.delete(f"{URL}{ordem_id}/").status_code, 403)

        self.assertTrue(OrdemManutencao.objects.filter(pk=ordem_id).exists())

    def test_logs_da_ordem_sao_somente_leitura(self):
        ordem_id = self.criar_ordem(self.suporte).data["id"]
        url_logs = f"{URL}{ordem_id}/logs/"

        self.assertEqual(self.client.get(url_logs).status_code, 200)
        self.assertIn(self.client.post(url_logs, {}, format="json").status_code, (403, 405))
