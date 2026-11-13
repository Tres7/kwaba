import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .infrastructure.persistence.models import UserModel

__all__ = [
    'Compte', 'ROLES', 'attacher', 'candidatures_refusees', 'compte', 'comptes', 'comptes_actifs', 'comptes_de_role',
    'compte_demo', 'condition_compte_actif', 'emails_actifs', 'emails_admins_section', 'hote_ou_candidat',
    'hotes_et_candidats', 'ids_actifs', 'ids_par_recherche', 'passer_hote', 'peut_gerer_annonces', 'retirer_role_hote',
    'revoquer_jetons', 'statistiques',
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
    candidature_hote: str = ''

    is_authenticated = True

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
                  avatar_url=u.avatar.url if u.avatar else None, candidature_hote=u.candidature_hote)


def hote_ou_candidat(utilisateur) -> bool:
    """Host, or traveller preparing their first listing (they stay a traveller until an agent validates it)."""
    return utilisateur.role == 'hote' or utilisateur.candidature_hote == 'ouverte'


def peut_gerer_annonces(utilisateur) -> bool:
    """May prepare listings: drafts, photos, identity document, payout account."""
    return utilisateur.role == 'admin' or hote_ou_candidat(utilisateur)


def passer_hote(user_id: uuid.UUID) -> bool:
    """First listing validated by an agent: the traveller becomes a host. False if they already had another role."""
    return bool(UserModel.objects.filter(pk=user_id, role='voyageur').update(
        role='hote', candidature_hote='', candidature_motif=''))


def retirer_role_hote(user_id: uuid.UUID, candidature: bool) -> bool:
    """Host from before the candidatures, without a validated listing: back to traveller, candidate if they had started."""
    return bool(UserModel.objects.filter(pk=user_id, role='hote').update(
        role='voyageur', candidature_hote='ouverte' if candidature else ''))


def candidatures_refusees(user_ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
    return set(UserModel.objects.filter(pk__in=list(user_ids), candidature_hote='refusee').values_list('id', flat=True))


def compte(user_id: uuid.UUID | None) -> Compte | None:
    if user_id is None:
        return None
    u = UserModel.objects.filter(pk=user_id).first()
    return _compte(u) if u else None


def comptes(user_ids: Iterable[uuid.UUID | None]) -> dict[uuid.UUID, Compte]:
    ids = {i for i in user_ids if i is not None}
    return {u.id: _compte(u) for u in UserModel.objects.filter(pk__in=ids)} if ids else {}


def attacher(objets: Iterable, *champs: str) -> list:
    """Loads in one query the accounts read through the `<champ>` cached property of each object."""
    objets = list(objets)
    trouves = comptes(getattr(o, f'{c}_id') for o in objets for c in champs)
    for o in objets:
        for c in champs:
            o.__dict__[c] = trouves.get(getattr(o, f'{c}_id'))
    return objets


def compte_demo(email: str, mot_de_passe: str, **champs) -> tuple[Compte, bool]:
    """Demo account (seed_demo command): created once with this password, then left as it is."""
    u, cree = UserModel.objects.get_or_create(email=email, defaults=champs)
    if cree:
        u.set_password(mot_de_passe)
        u.save()
    return _compte(u), cree


def ids_par_recherche(texte: str) -> list[uuid.UUID]:
    return list(UserModel.objects.filter(
        Q(email__icontains=texte) | Q(first_name__icontains=texte) | Q(last_name__icontains=texte)
    ).values_list('id', flat=True))


def ids_actifs(roles: Iterable[str]) -> list[uuid.UUID]:
    return list(UserModel.objects.filter(role__in=list(roles), is_active=True).values_list('id', flat=True))


def condition_compte_actif(champ: str) -> Exists:
    """SQL condition: the account whose id is in field `champ` of the outer query is active (neither closed nor banned)."""
    return Exists(UserModel.objects.filter(pk=OuterRef(champ), is_active=True))


def comptes_actifs(roles: Iterable[str], texte: str = '', ids: Iterable[uuid.UUID] | None = None,
                   limite: int | None = None) -> list[Compte]:
    qs = UserModel.objects.filter(role__in=list(roles), is_active=True).order_by('first_name', 'last_name')
    if texte:
        qs = qs.filter(Q(email__icontains=texte) | Q(first_name__icontains=texte) | Q(last_name__icontains=texte))
    if ids is not None:
        qs = qs.filter(pk__in=list(ids))
    return [_compte(u) for u in (qs[:limite] if limite else qs)]


def hotes_et_candidats(texte: str = '', limite: int | None = None) -> list[Compte]:
    qs = UserModel.objects.filter(Q(role='hote') | Q(candidature_hote='ouverte'), is_active=True).order_by(
        'first_name', 'last_name')
    if texte:
        qs = qs.filter(Q(email__icontains=texte) | Q(first_name__icontains=texte) | Q(last_name__icontains=texte))
    return [_compte(u) for u in (qs[:limite] if limite else qs)]


def comptes_de_role(role: str) -> list[Compte]:
    """Every account of a role, deactivated ones included."""
    return [_compte(u) for u in UserModel.objects.filter(role=role).order_by('date_joined')]


def emails_actifs(roles: Iterable[str], limite: int | None = None) -> list[str]:
    emails = UserModel.objects.filter(role__in=list(roles), is_active=True).order_by('date_joined').values_list(
        'email', flat=True)
    return list(emails[:limite] if limite else emails)


def emails_admins_section(section: str) -> list[str]:
    """Active admins who see a back-office section (securite.permissions.a_acces_section): super admins, admins
    without limits and admins granted that section, whose access has not ended."""
    maintenant = timezone.now()
    return list(
        UserModel.objects.filter(role='admin', is_active=True)
        .filter(Q(is_superuser=True) | Q(admin_sections__isnull=True) | Q(admin_sections__contains=[section]))
        .filter(Q(admin_expire_le__isnull=True) | Q(admin_expire_le__gt=maintenant))
        .order_by('date_joined').values_list('email', flat=True))


def statistiques(depuis: datetime) -> dict:
    return UserModel.objects.aggregate(
        total=Count('id'),
        nouveaux_30j=Count('id', filter=Q(date_joined__gte=depuis)),
        hotes=Count('id', filter=Q(role='hote')),
        candidats=Count('id', filter=Q(candidature_hote='ouverte')),
        desactives=Count('id', filter=Q(is_active=False)),
    )


def revoquer_jetons(user_id) -> None:
    """Blacklists all the user's refresh tokens: all their sessions are closed.

    Access tokens issued before a password change are refused by CHECK_REVOKE_TOKEN.
    """
    for jeton in OutstandingToken.objects.filter(user_id=user_id).exclude(blacklistedtoken__isnull=False):
        BlacklistedToken.objects.get_or_create(token=jeton)
