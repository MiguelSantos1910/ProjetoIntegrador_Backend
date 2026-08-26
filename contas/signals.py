"""
Cria automaticamente um Perfil (papel=ALUNO por padrão) sempre que um novo
usuário do Django é criado pelo /admin. Ajuste o papel manualmente no admin
depois de criar o usuário (ex.: trocar para PROFESSOR ou SUPORTE).
"""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Perfil


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_perfil_padrao(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.get_or_create(usuario=instance, defaults={"papel": Perfil.Papel.ALUNO})
