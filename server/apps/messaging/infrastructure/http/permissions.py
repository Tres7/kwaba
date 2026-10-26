from rest_framework.permissions import BasePermission


class IsVerified(BasePermission):
    """Anti-abuse: only a verified email address can start a thread or send a message."""

    message = "Vérifiez votre adresse email pour utiliser la messagerie."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_verified', False)
        )
