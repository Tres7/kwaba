# JSON validation, deserialization and serialization
import hashlib
import re

from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection, transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.domain.entities.User import UserRole

# The admin role can never be chosen at public sign-up
PUBLIC_ROLES = [UserRole.VOYAGEUR.value, UserRole.HOTE.value]


class RegisterSerializer(serializers.Serializer):
    email      = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name  = serializers.CharField(max_length=150)
    password   = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(min_length=8, write_only=True)
    role       = serializers.ChoiceField(choices=PUBLIC_ROLES, default=UserRole.VOYAGEUR.value)
    phone      = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_first_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Le prénom est requis.')
        return value

    def validate_last_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Le nom est requis.')
        return value

    def validate_phone(self, value):
        if not value:
            return None
        cleaned = re.sub(r'[\s.\-()]', '', value)
        if cleaned.startswith('00'):
            cleaned = '+' + cleaned[2:]
        if not re.match(r'^\+\d{8,15}$', cleaned):
            raise serializers.ValidationError(
                'Numéro invalide. Utilisez le format international, ex : +228 90 00 00 00.'
            )
        return cleaned

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Les mots de passe ne correspondent pas.'})
        try:
            validate_password(data['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return data


class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    code     = serializers.RegexField(r'^\d{6}$', error_messages={'invalid': 'Le code contient 6 chiffres.'})
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(min_length=8, write_only=True)

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Les mots de passe ne correspondent pas.'})
        try:
            validate_password(data['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return data


class RefreshWithGracePeriodSerializer(TokenRefreshSerializer):
    """Rotation with blacklist, and grace period for parallel renewals of the same token.

    The first call renews the pair and blacklists the old refresh token. During
    JWT_REFRESH_GRACE_SECONDS, the old token returns this same new pair instead of a 401;
    afterwards it is refused. Simultaneous calls are serialised by a PostgreSQL lock: the blacklist
    and the cache (DatabaseCache) are committed in the same transaction, so the next call finds the pair.
    """

    def validate(self, attrs):
        empreinte = hashlib.sha256(attrs['refresh'].encode()).digest()
        cle = f'jwt_refresh_grace:{empreinte.hex()}'
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [int.from_bytes(empreinte[:8], 'big', signed=True)])
            deja_renouvele = cache.get(cle)
            if deja_renouvele is not None:
                # Reading the new token fails if it is blacklisted: a session closed in the meantime stays closed
                RefreshToken(deja_renouvele['refresh'])
                return deja_renouvele
            data = super().validate(attrs)
            cache.set(cle, data, timeout=settings.JWT_REFRESH_GRACE_SECONDS)
            return data

