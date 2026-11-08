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
            {"password": "Nova-Senha-789", "senha_atual": SENHA},
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


class AdministracaoContasTestCase(APITestCase):
    """Regressões da revisão do back (itens 2, 3, 6, 9 e N11)."""

    def setUp(self):
        self.aluno = criar_usuario("aluno_adm")
        self.professor = criar_usuario("professor_adm", Perfil.Papel.PROFESSOR)
        self.root = User.objects.create_superuser(
            username="root_adm", password=SENHA, email="root@example.com"
        )

    def url(self, usuario, sufixo=""):
        return f"/api/contas/usuarios/{usuario.id}/{sufixo}"

    def test_professor_nao_administra_superusuario(self):
        self.client.force_authenticate(self.professor)

        self.assertEqual(
            self.client.patch(
                self.url(self.root, "senha/"), {"password": "Invasao-Senha-999"}, format="json"
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(self.url(self.root), {"is_active": False}, format="json").status_code,
            403,
        )
        self.assertEqual(self.client.delete(self.url(self.root)).status_code, 403)

        self.root.refresh_from_db()
        self.assertTrue(self.root.is_active)
        self.assertTrue(self.root.check_password(SENHA))

    def test_propria_senha_exige_senha_atual(self):
        self.client.force_authenticate(self.aluno)

        sem = self.client.patch(
            self.url(self.aluno, "senha/"), {"password": "Nova-Senha-789"}, format="json"
        )
        errada = self.client.patch(
            self.url(self.aluno, "senha/"),
            {"password": "Nova-Senha-789", "senha_atual": "errada"},
            format="json",
        )

        self.assertEqual(sem.status_code, 400)
        self.assertEqual(errada.status_code, 400)
        self.assertIn("senha_atual", errada.data)
        self.aluno.refresh_from_db()
        self.assertTrue(self.aluno.check_password(SENHA))
        self.assertTrue(
            LogConta.objects.filter(usuario=self.aluno, tipo_evento="ALTERACAO_SENHA_FALHA").exists()
        )

    def test_troca_de_senha_encerra_sessoes(self):
        login = self.client.post(
            "/api/token/", {"username": "aluno_adm", "password": SENHA}, format="json"
        )
        refresh = login.data["refresh"]

        self.client.force_authenticate(self.aluno)
        resposta = self.client.patch(
            self.url(self.aluno, "senha/"),
            {"password": "Nova-Senha-789", "senha_atual": SENHA},
            format="json",
        )
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.client.force_authenticate(None)

        renovar = self.client.post("/api/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(renovar.status_code, 401)
        self.assertTrue(
            LogConta.objects.filter(usuario=self.aluno, tipo_evento="SENHA_ALTERADA").exists()
        )

    def test_professor_redefine_senha_de_aluno(self):
        self.client.force_authenticate(self.professor)

        resposta = self.client.patch(
            self.url(self.aluno, "senha/"), {"password": "Nova-Senha-789"}, format="json"
        )

        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.aluno.refresh_from_db()
        self.assertTrue(self.aluno.check_password("Nova-Senha-789"))

    def test_mudanca_de_papel_e_desativacao_geram_log(self):
        self.client.force_authenticate(self.professor)

        self.client.patch(self.url(self.aluno), {"papel": "SUPORTE"}, format="json")
        self.client.patch(self.url(self.aluno), {"is_active": False}, format="json")

        eventos = set(
            LogConta.objects.filter(usuario=self.aluno).values_list("tipo_evento", flat=True)
        )
        self.assertIn("PAPEL_ALTERADO", eventos)
        self.assertIn("CONTA_DESATIVADA", eventos)

    def test_professor_nao_rebaixa_a_si_mesmo(self):
        self.client.force_authenticate(self.professor)

        resposta = self.client.patch(self.url(self.professor), {"papel": "ALUNO"}, format="json")

        self.assertEqual(resposta.status_code, 403)
        self.professor.perfil.refresh_from_db()
        self.assertEqual(self.professor.perfil.papel, Perfil.Papel.PROFESSOR)

    def test_exclusao_gera_log(self):
        self.client.force_authenticate(self.professor)

        self.assertEqual(self.client.delete(self.url(self.aluno)).status_code, 204)
        self.assertTrue(LogConta.objects.filter(tipo_evento="USUARIO_EXCLUIDO").exists())

    def test_evento_sem_usuario_aparece_como_nao_identificado(self):
        self.client.post("/api/token/", {"username": "nao_existe", "password": "x"}, format="json")

        self.client.force_authenticate(self.professor)
        resposta = self.client.get("/api/contas/auditoria/")
        nomes = [log["usuario_nome"] for log in resposta.data if log["tipo_evento"] == "LOGIN_FALHA"]
        self.assertIn("Não identificado", nomes)


class LimpezaTentativasTestCase(APITestCase):
    """N11: tentativas de login antigas (e de usuários inexistentes) são apagadas."""

    def test_tentativas_antigas_sao_removidas_na_proxima_falha(self):
        from datetime import timedelta

        from django.utils import timezone

        from .models import TentativaLogin

        self.client.post("/api/token/", {"username": "fantasma", "password": "x"}, format="json")
        TentativaLogin.objects.update(atualizado_em=timezone.now() - timedelta(days=2))

        self.client.post("/api/token/", {"username": "outro", "password": "x"}, format="json")

        self.assertFalse(TentativaLogin.objects.filter(username="fantasma").exists())
        self.assertTrue(TentativaLogin.objects.filter(username="outro").exists())


class ListaUsuariosAtualizadaTestCase(APITestCase):
    """A lista do professor precisa mostrar contas criadas depois da 1ª consulta."""

    def test_usuario_criado_aparece_na_lista(self):
        professor = criar_usuario("professor_lista", Perfil.Papel.PROFESSOR)
        self.client.force_authenticate(professor)

        antes = self.client.get("/api/contas/usuarios/")
        self.assertEqual(antes.status_code, 200)

        self.client.force_authenticate(None)
        cadastro = self.client.post(
            "/api/contas/usuarios/",
            {"username": "aluno_novo_lista", "password": SENHA, "email": "novo@example.com"},
            format="json",
        )
        self.assertEqual(cadastro.status_code, 201, cadastro.data)

        self.client.force_authenticate(professor)
        depois = self.client.get("/api/contas/usuarios/")

        nomes = [usuario["username"] for usuario in depois.data]
        self.assertIn("aluno_novo_lista", nomes)
