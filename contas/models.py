from django.conf import settings
from django.db import models


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


class LogConta(models.Model):

    class TipoEvento(models.TextChoices):
        CADASTRO = "CADASTRO", "Cadastro"
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_conta",
    )

    tipo_evento = models.CharField(
        max_length=20,
        choices=TipoEvento.choices,
    )

    descricao = models.TextField(blank=True)

    ip = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data"]
        verbose_name = "Log de conta"
        verbose_name_plural = "Logs de contas"

    def __str__(self):
        usuario = (
            self.usuario.username
            if self.usuario
            else "Usuário removido"
        )

        return (
            f"{usuario} - {self.get_tipo_evento_display()} "
            f"em {self.data:%d/%m/%Y %H:%M}"
        )
