"""
Testes de backup e restauração (evidência do item B14 da revisão).
Rode com: python manage.py test backups
"""

import shutil
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.test import APITransactionTestCase

from ativos.models import Ativo
from contas.models import LogConta


URL = "/api/backups/"


def url_restaurar(nome):
    return f"{URL}{nome}/restaurar/"


# A restauração copia o backup para dentro do banco em uso, o que não pode
# acontecer dentro de uma transação; por isso APITransactionTestCase.
class BackupAPITestCase(APITransactionTestCase):

    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.override = override_settings(BACKUP_DIR=self.pasta, BACKUP_MAX=3)
        self.override.enable()

        self.professor = self.criar_usuario("professor_teste", "PROFESSOR")
        self.suporte = self.criar_usuario("suporte_teste", "SUPORTE")
        self.aluno = self.criar_usuario("aluno_teste", "ALUNO")

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.pasta, ignore_errors=True)

    def criar_usuario(self, username, papel):
        usuario = User.objects.create_user(username=username, password="Senha-teste-123")
        usuario.perfil.papel = papel
        usuario.perfil.save()
        return usuario

    def gerar_backup(self):
        self.client.force_authenticate(self.professor)
        resposta = self.client.post(URL)
        self.assertEqual(resposta.status_code, 201, resposta.data)
        return resposta.data["nome"]

    # -- Permissões ---------------------------------------------------------

    def test_sem_login_recebe_401(self):
        self.assertEqual(self.client.get(URL).status_code, 401)

    def test_aluno_e_suporte_recebem_403(self):
        for usuario in (self.aluno, self.suporte):
            self.client.force_authenticate(usuario)
            self.assertEqual(self.client.get(URL).status_code, 403)
            self.assertEqual(self.client.post(URL).status_code, 403)
            self.assertEqual(
                self.client.post(
                    url_restaurar("db_20260101_000000.sqlite3"),
                    {"confirmacao": "RESTAURAR"},
                ).status_code,
                403,
            )

        self.assertEqual(list(Path(self.pasta).iterdir()), [])

    # -- Backup ---------------------------------------------------------------

    def test_professor_gera_e_lista_backup(self):
        Ativo.objects.create(tipo="GABINETE", descricao="WORKSTATION", sala="B-111")

        nome = self.gerar_backup()

        self.assertTrue((Path(self.pasta) / nome).is_file())
        self.assertTrue(
            LogConta.objects.filter(tipo_evento="BACKUP_CRIADO", usuario=self.professor).exists()
        )

        lista = self.client.get(URL).data
        self.assertEqual(lista[0]["nome"], nome)
        self.assertEqual(lista[0]["contagens"], {"ativos": 1, "usuarios": 3, "ordens": 0})

    def test_mantem_apenas_os_mais_recentes(self):
        for _ in range(5):
            self.gerar_backup()

        self.assertEqual(len(list(Path(self.pasta).glob("db_*.sqlite3"))), 3)

    # -- Restauração ------------------------------------------------------------

    def test_restaurar_exige_confirmacao(self):
        nome = self.gerar_backup()

        resposta = self.client.post(url_restaurar(nome), {})
        self.assertEqual(resposta.status_code, 400)

    def test_nome_invalido_ou_inexistente(self):
        self.client.force_authenticate(self.professor)

        for nome in ("db.sqlite3", "..%2Fdb.sqlite3", "qualquer.txt"):
            resposta = self.client.post(url_restaurar(nome), {"confirmacao": "RESTAURAR"})
            self.assertIn(resposta.status_code, (400, 404), nome)

        resposta = self.client.post(
            url_restaurar("db_20200101_000000.sqlite3"), {"confirmacao": "RESTAURAR"}
        )
        self.assertEqual(resposta.status_code, 404)
        self.assertTrue(LogConta.objects.filter(tipo_evento="BACKUP_FALHA").exists())

    def test_restaurar_volta_ao_estado_do_backup(self):
        ativo = Ativo.objects.create(tipo="MONITOR", descricao="MONITOR ORIGINAL", sala="B-111")

        nome = self.gerar_backup()

        # Depois do backup: altera um ativo e cadastra outro.
        ativo.descricao = "MONITOR ALTERADO"
        ativo.save()
        Ativo.objects.create(tipo="TECLADO", descricao="TECLADO NOVO", sala="B-111")

        resposta = self.client.post(url_restaurar(nome), {"confirmacao": "RESTAURAR"})
        self.assertEqual(resposta.status_code, 200, resposta.data)

        # Voltou ao estado do backup.
        self.assertEqual(Ativo.objects.count(), 1)
        self.assertEqual(Ativo.objects.get(pk=ativo.pk).descricao, "MONITOR ORIGINAL")

        # O estado anterior foi salvo e a restauração ficou registrada.
        seguranca = resposta.data["backup_seguranca"]["nome"]
        self.assertTrue(seguranca.startswith("pre_restauracao_"))
        self.assertTrue((Path(self.pasta) / seguranca).is_file())
        self.assertTrue(LogConta.objects.filter(tipo_evento="BACKUP_RESTAURADO").exists())

    def test_restauracao_pode_ser_desfeita(self):
        Ativo.objects.create(tipo="MESA", descricao="MESA ANTIGA", sala="B-111")
        nome = self.gerar_backup()

        Ativo.objects.create(tipo="MESA", descricao="MESA NOVA", sala="B-111")

        seguranca = self.client.post(
            url_restaurar(nome), {"confirmacao": "RESTAURAR"}
        ).data["backup_seguranca"]["nome"]
        self.assertEqual(Ativo.objects.count(), 1)

        resposta = self.client.post(url_restaurar(seguranca), {"confirmacao": "RESTAURAR"})
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertEqual(Ativo.objects.count(), 2)
