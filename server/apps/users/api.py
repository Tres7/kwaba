import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Count, Q
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .infrastructure.persistence.models import UserModel

__all__ = [
    'Compte', 'ROLES', 'compte', 'comptes', 'emails_actifs', 'ids_actifs', 'ids_par_recherche', 'revoquer_jetons',
    'statistiques',
]

ROLES = [code for code, _ in UserModel.ROLE_CHOICES]
LIBELLES_ROLES = dict(UserModel.ROLE_CHOICES)


@dataclass(frozen=True)
class Compte:
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    phone: str | None
    role: str
    is_active: bool
    is_verified: bool
    date_joined: datetime
    avatar_url: str | None

    @property
    def pk(self) -> uuid.UUID:
        return self.id

    def get_full_name(self) -> str:
        return f'{self.first_name} {self.last_name}'.strip()

    def get_role_display(self) -> str:
        return LIBELLES_ROLES.get(self.role, self.role)


def _compte(u: UserModel) -> Compte:
    return Compte(id=u.id, email=u.email, first_name=u.first_name, last_name=u.last_name, phone=u.phone, role=u.role,
                  is_active=u.is_active, is_verified=u.is_verified, date_joined=u.date_joined,
                  avatar_url=u.avatar.url if u.avatar else None)


def compte(user_id: uuid.UUID | None) -> Compte | None:
    if user_id is None:
        return None
    u = UserModel.objects.filter(pk=user_id).first()
    return _compte(u) if u else None


def comptes(user_ids: Iterable[uuid.UUID | None]) -> dict[uuid.UUID, Compte]:
    ids = {i for i in user_ids if i is not None}
    return {u.id: _compte(u) for u in UserModel.objects.filter(pk__in=ids)} if ids else {}


def ids_par_recherche(texte: str) -> list[uuid.UUID]:
    return list(UserModel.objects.filter(
        Q(email__icontains=texte) | Q(first_name__icontains=texte) | Q(last_name__icontains=texte)
    ).values_list('id', flat=True))


def ids_actifs(roles: Iterable[str]) -> list[uuid.UUID]:
    return list(UserModel.objects.filter(role__in=list(roles), is_active=True).values_list('id', flat=True))


def emails_actifs(roles: Iterable[str], limite: int | None = None) -> list[str]:
    emails = UserModel.objects.filter(role__in=list(roles), is_active=True).order_by('date_joined').values_list(
        'email', flat=True)
    return list(emails[:limite] if limite else emails)


def statistiques(depuis: datetime) -> dict:
    return UserModel.objects.aggregate(
        total=Count('id'),
        nouveaux_30j=Count('id', filter=Q(date_joined__gte=depuis)),
        hotes=Count('id', filter=Q(role='hote')),
        desactives=Count('id', filter=Q(is_active=False)),
    )


def revoquer_jetons(user_id) -> None:
    """Blacklists all the user's refresh tokens: all their sessions are closed.

    Access tokens issued before a password change are refused by CHECK_REVOKE_TOKEN.
    """
    for jeton in OutstandingToken.objects.filter(user_id=user_id).exclude(blacklistedtoken__isnull=False):
        BlacklistedToken.objects.get_or_create(token=jeton)
