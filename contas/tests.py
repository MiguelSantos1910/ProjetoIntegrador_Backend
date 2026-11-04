"""
Testes básicos de segurança de contas (evidência do E4, item B14).
Rode com: python manage.py test contas

Cobrem login, falha e bloqueio por tentativas, logout que invalida o
refresh token, cadastro público sempre como ALUNO, senha fraca recusada,
escalada de privilégio e acesso às contas de outros usuários.
"""

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from .models import LogConta, Perfil


SENHA = "Senha-Forte-123"


def criar_usuario(username, papel=Perfil.Papel.ALUNO):
    usuario = User.objects.create_user(username=username, password=SENHA)
    usuario.perfil.papel = papel
    usuario.perfil.save()
    return usuario


class LoginTestCase(APITestCase):

    def setUp(self):
        self.aluno = criar_usuario("aluno_teste")

    def login(self, username="aluno_teste", password=SENHA):
        return self.client.post(
            "/api/token/",
            {"username": username, "password": password},
            format="json",
        )

    def test_login_correto_retorna_tokens_e_grava_log(self):
        resposta = self.login()

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("access", resposta.data)
        self.assertIn("refresh", resposta.data)
        self.assertTrue(
            LogConta.objects.filter(usuario=self.aluno, tipo_evento="LOGIN").exists()
        )

    def test_senha_errada_retorna_401_e_grava_falha(self):
        resposta = self.login(password="senha-errada")

        self.assertEqual(resposta.status_code, 401)
        self.assertNotIn("access", resposta.data)
        self.assertTrue(LogConta.objects.filter(tipo_evento="LOGIN_FALHA").exists())

    def test_log_nao_grava_a_senha(self):
        self.login(password="senha-errada-secreta")

        for log in LogConta.objects.all():
            self.assertNotIn("senha-errada-secreta", log.descricao)

    def test_bloqueio_na_quinta_tentativa(self):
        for _ in range(4):
            self.assertEqual(self.login(password="errada").status_code, 401)

        # 5ª tentativa errada: bloqueio (429).
        self.assertEqual(self.login(password="errada").status_code, 429)

        # Durante o bloqueio, nem a senha correta entra.
        self.assertEqual(self.login().status_code, 429)
        self.assertTrue(LogConta.objects.filter(tipo_evento="LOGIN_BLOQUEADO").exists())

        # O bloqueio é por usuário: outra conta continua entrando.
        criar_usuario("outro_aluno")
        self.assertEqual(self.login(username="outro_aluno").status_code, 200)

    def test_rotas_protegidas_exigem_token(self):
        for url in ("/api/ativos/", "/api/contas/me/", "/api/ordens_manutencao/"):
            self.assertEqual(self.client.get(url).status_code, 401, url)


class LogoutTestCase(APITestCase):

    def test_logout_invalida_o_refresh_token(self):
        criar_usuario("aluno_logout")
        tokens = self.client.post(
            "/api/token/",
            {"username": "aluno_logout", "password": SENHA},
            format="json",
        ).data

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resposta = self.client.post(
            "/api/contas/logout/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(LogConta.objects.filter(tipo_evento="LOGOUT").exists())

        # O refresh antigo não gera mais tokens.
        self.client.credentials()
        resposta = self.client.post(
            "/api/token/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(resposta.status_code, 401)


class CadastroTestCase(APITestCase):

    URL = "/api/contas/usuarios/"

    def dados(self, **extra):
        return {
            "username": "novo_aluno",
            "email": "novo@exemplo.com",
            "password": SENHA,
            **extra,
        }

    def test_cadastro_publico_cria_aluno(self):
        resposta = self.client.post(self.URL, self.dados(), format="json")

        self.assertEqual(resposta.status_code, 201, resposta.data)
        usuario = User.objects.get(username="novo_aluno")
        self.assertEqual(usuario.perfil.papel, Perfil.Papel.ALUNO)
        # A senha é guardada com hash, nunca em texto.
        self.assertNotEqual(usuario.password, SENHA)
        self.assertTrue(usuario.check_password(SENHA))

    def test_cadastro_publico_nao_escolhe_papel(self):
        resposta = self.client.post(
            self.URL, self.dados(papel="PROFESSOR"), format="json"
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(User.objects.filter(username="novo_aluno").exists())

    def test_senha_fraca_recusada(self):
        resposta = self.client.post(self.URL, self.dados(password="1"), format="json")

        self.assertEqual(resposta.status_code, 400)
        self.assertFalse(User.objects.filter(username="novo_aluno").exists())
        self.assertTrue(LogConta.objects.filter(tipo_evento="CADASTRO_FALHA").exists())


class PermissoesContasTestCase(APITestCase):

    def setUp(self):
        self.aluno = criar_usuario("aluno_perm")
        self.suporte = criar_usuario("suporte_perm", Perfil.Papel.SUPORTE)
        self.professor = criar_usuario("professor_perm", Perfil.Papel.PROFESSOR)

    def test_aluno_nao_se_promove_a_professor(self):
        self.client.force_authenticate(self.aluno)

        resposta = self.client.patch(
            f"/api/contas/usuarios/{self.aluno.id}/", {"papel": "PROFESSOR"}, format="json"
        )

        self.assertEqual(resposta.status_code, 403)
        self.aluno.perfil.refresh_from_db()
        self.assertEqual(self.aluno.perfil.papel, Perfil.Papel.ALUNO)

    def test_aluno_e_suporte_veem_so_a_propria_conta(self):
        for usuario in (self.aluno, self.suporte):
            self.client.force_authenticate(usuario)
            resposta = self.client.get("/api/contas/usuarios/")

            self.assertEqual(resposta.status_code, 200)
            self.assertEqual([u["id"] for u in resposta.data], [usuario.id])

    def test_nao_troca_senha_de_outro_usuario(self):
        self.client.force_authenticate(self.aluno)

        resposta = self.client.patch(
            f"/api/contas/usuarios/{self.suporte.id}/senha/",
            {"password": "Outra-Senha-456"},
            format="json",
        )

        self.assertIn(resposta.status_code, (403, 404))
        self.suporte.refresh_from_db()
        self.assertTrue(self.suporte.check_password(SENHA))

    def test_troca_a_propria_senha(self):
        self.client.force_authenticate(self.aluno)

        resposta = self.client.patch(
            f"/api/contas/usuarios/{self.aluno.id}/senha/",
            {"password": "Nova-Senha-789"},
            format="json",
        )

        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.aluno.refresh_from_db()
        self.assertTrue(self.aluno.check_password("Nova-Senha-789"))

    def test_auditoria_somente_professor(self):
        for usuario in (self.aluno, self.suporte):
            self.client.force_authenticate(usuario)
            self.assertEqual(self.client.get("/api/contas/auditoria/").status_code, 403)

        self.client.force_authenticate(self.professor)
        self.assertEqual(self.client.get("/api/contas/auditoria/").status_code, 200)

    def test_logs_nao_podem_ser_alterados(self):
        self.client.force_authenticate(self.professor)

        self.assertEqual(
            self.client.post("/api/contas/auditoria/", {}, format="json").status_code, 405
        )
