from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.users.admins import retirer_si_expire


class AuthentificationJWT(JWTAuthentication):
    """Every role check of the API then sees a temporary admin as expired, wherever it is written."""

    def get_user(self, validated_token):
        utilisateur = super().get_user(validated_token)
        retirer_si_expire(utilisateur)
        return utilisateur
