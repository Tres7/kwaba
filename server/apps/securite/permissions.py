from rest_framework.permissions import IsAuthenticated


class EstAdministrateur(IsAuthenticated):
    """Back-office: role read from the database at every request (request.user), never from the frontend session."""

    message = "Accès réservé aux administrateurs."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'
