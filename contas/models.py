from django.conf import settings
from django.db import models


class Perfil(models.Model):
    """
    Estende o usuário padrão do Django com o papel dessa pessoa no sistema.
    Os três papéis previstos pelo projeto (Documento 1, Usuários U01-U03):
    PROFESSOR (ex.: Eduardo, responsável pelo laboratório B-111), ALUNO e SUPORTE.
    """

    class Papel(models.TextChoices):
        PROFESSOR = "PROFESSOR", "Professor"
        ALUNO = "ALUNO", "Aluno"
        SUPORTE = "SUPORTE", "Suporte técnico"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    papel = models.CharField(max_length=20, choices=Papel.choices)

    def __str__(self):
        return f"{self.usuario.username} ({self.get_papel_display()})"
