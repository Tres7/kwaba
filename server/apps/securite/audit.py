import logging

from .limites import ip_client
from .models import JournalAuditModel

logger = logging.getLogger('apps.securite')


def journaliser(action: str, request=None, utilisateur=None, email: str = '', **details) -> None:
    """Adds an entry to the audit log. Must never make the calling request fail.

    `utilisateur`: instance or id. Never pass a password, a code nor a token.
    """
    try:
        utilisateur_id = getattr(utilisateur, 'pk', utilisateur)
        JournalAuditModel.objects.create(
            action=action,
            utilisateur_id=utilisateur_id,
            email=(email or getattr(utilisateur, 'email', '') or '')[:254],
            ip=ip_client(request) if request is not None else None,
            details=details,
        )
    except Exception:
        logger.exception("Journal d'audit : écriture impossible (%s)", action)
