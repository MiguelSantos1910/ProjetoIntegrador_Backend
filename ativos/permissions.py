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
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if request.method in SAFE_METHODS:
            return True

        perfil = getattr(user, "perfil", None)
        papel = getattr(perfil, "papel", None)

        return papel in {"PROFESSOR", "SUPORTE"}
