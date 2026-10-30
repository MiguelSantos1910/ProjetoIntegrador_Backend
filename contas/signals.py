
"""
Cria automaticamente um Perfil sempre que um novo usuário
do Django é criado.

Regras:
- Superusuário: PROFESSOR
- Usuário comum: ALUNO

Perfis existentes não são sobrescritos.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Perfil


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_perfil_padrao(sender, instance, created, **kwargs):
    """
    Cria o perfil padrão do usuário após sua criação.
    """

    if not created:
        return

    # Define o perfil conforme o tipo de usuário.
    papel_padrao = (
        Perfil.Papel.PROFESSOR
        if instance.is_superuser
        else Perfil.Papel.ALUNO
    )

    Perfil.objects.get_or_create(
        usuario=instance,
        defaults={
            "papel": papel_padrao,
        },
    )
