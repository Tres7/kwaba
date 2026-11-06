"""Temporary admins: at the end date, the account goes back to the role it had before."""
from django.db.models import Case, F, Value, When
from django.utils import timezone

from apps.securite.audit import journaliser

from .infrastructure.persistence.models import UserModel


def _expires():
    return UserModel.objects.filter(role='admin', is_superuser=False, admin_expire_le__lte=timezone.now())


def retirer_si_expire(utilisateur) -> None:
    """Called at every authenticated request: the account loses its rights as soon as the date is passed."""
    if utilisateur.role != 'admin' or utilisateur.admin_expire_le is None or utilisateur.admin_expire_le > timezone.now():
        return
    if _retirer(_expires().filter(pk=utilisateur.pk)):
        utilisateur.refresh_from_db(fields=['role', 'admin_sections', 'admin_expire_le', 'role_avant_admin'])


def retirer_expires() -> int:
    """Scheduled task: an admin who no longer signs in must not keep receiving the emails of the team."""
    return _retirer(_expires())


def _retirer(admins) -> int:
    comptes = list(admins.values('pk', 'email', 'role_avant_admin'))
    nombre = admins.update(
        role=Case(When(role_avant_admin='', then=Value('voyageur')), default=F('role_avant_admin')),
        admin_sections=None, admin_expire_le=None, role_avant_admin='',
    )
    for compte in comptes:
        journaliser('admin_expire', utilisateur=compte['pk'], email=compte['email'],
                    apres=compte['role_avant_admin'] or 'voyageur')
    return nombre
