
from rest_framework.permissions import SAFE_METHODS, BasePermission


class PodeAlterarOrdemManutencao(BasePermission):
    """
    Permissões para ordens de manutenção:

    - Qualquer usuário autenticado pode consultar (GET, HEAD, OPTIONS).
    - Professor e suporte técnico podem criar e editar.
    - Alunos possuem somente leitura.
    - Exclusão de ordens não é permitida.
    """

    message = "Você não possui permissão para realizar esta operação."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if request.method in SAFE_METHODS:
            return True

        if request.method == "DELETE":
            return False

        perfil = getattr(user, "perfil", None)
        papel = getattr(perfil, "papel", None)

        return papel in {"PROFESSOR", "SUPORTE"}

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)

class PodeConsultarLogOrdem(BasePermission):
    """
    Usuários autenticados podem consultar os logs.
    Nenhum usuário pode modificá-los diretamente pela API.
    """

    message = "Os registros de histórico não podem ser modificados diretamente."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.method in SAFE_METHODS
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
