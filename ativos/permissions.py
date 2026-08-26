from rest_framework.permissions import SAFE_METHODS, BasePermission


class PodeAlterarAtivo(BasePermission):
    """
    Regra provisória de permissão (endurecer de verdade na atividade L4.1
    — Sprint 4: Segurança). Por enquanto:
      - Qualquer usuário autenticado pode LER (GET) os ativos.
      - Só professor e suporte técnico podem criar/editar/apagar.
    Alunos ficam só com leitura, que já cobre a jornada básica de consulta.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        papel = getattr(getattr(request.user, "perfil", None), "papel", None)
        return papel in ("PROFESSOR", "SUPORTE") or request.user.is_superuser
