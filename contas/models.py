
from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# PERFIL DO USUÁRIO
# ---------------------------------------------------------------------------

class Perfil(models.Model):

    class Papel(models.TextChoices):
        PROFESSOR = "PROFESSOR", "Professor"
        ALUNO = "ALUNO", "Aluno"
        SUPORTE = "SUPORTE", "Suporte técnico"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )

    papel = models.CharField(
        max_length=20,
        choices=Papel.choices,
        default=Papel.ALUNO,
    )

    def __str__(self):
        return f"{self.usuario.username} ({self.get_papel_display()})"


# ---------------------------------------------------------------------------
# LOGS DE AUDITORIA DAS CONTAS
# ---------------------------------------------------------------------------

class LogConta(models.Model):

    class TipoEvento(models.TextChoices):

        # Cadastro
        CADASTRO = "CADASTRO", "Cadastro"
        CADASTRO_FALHA = "CADASTRO_FALHA", "Falha no cadastro"

        # Autenticação
        LOGIN = "LOGIN", "Login"
        LOGIN_FALHA = "LOGIN_FALHA", "Falha no login"
        LOGIN_BLOQUEADO = "LOGIN_BLOQUEADO", "Login bloqueado"

        # Encerramento de sessão
        LOGOUT = "LOGOUT", "Logout"

        # Alteração de senha
        ALTERACAO_SENHA_FALHA = (
            "ALTERACAO_SENHA_FALHA",
            "Falha na alteração de senha",
        )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_conta",
    )

    tipo_evento = models.CharField(
        max_length=30,
        choices=TipoEvento.choices,
    )

    descricao = models.TextField(blank=True)

    ip = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    data = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-data"]
        verbose_name = "Log de conta"
        verbose_name_plural = "Logs de contas"

    def __str__(self):

        usuario = (
            self.usuario.username
            if self.usuario
            else "Usuário não identificado"
        )

        return (
            f"{usuario} - {self.get_tipo_evento_display()} "
            f"em {self.data:%d/%m/%Y %H:%M}"
        )


# ---------------------------------------------------------------------------
# CONTROLE DE TENTATIVAS DE LOGIN
# ---------------------------------------------------------------------------

class TentativaLogin(models.Model):

    username = models.CharField(
        max_length=255,
    )

    ip = models.CharField(
        max_length=45,
        blank=True,
        default="",
    )

    tentativas = models.PositiveSmallIntegerField(
        default=0,
    )

    bloqueado_ate = models.DateTimeField(
        null=True,
        blank=True,
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Tentativa de Login"
        verbose_name_plural = "Tentativas de Login"

        constraints = [
            models.UniqueConstraint(
                fields=["username", "ip"],
                name="unique_tentativa_login_usuario_ip",
            )
        ]

    def __str__(self):
        return f"{self.username} - {self.tentativas} tentativas"
