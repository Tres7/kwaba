"""Anti-fraud alerts: every bypass attempt is recorded for an administrator.

At the SEUIL-th report of the same account over 30 days, the administrators are notified by email (once).
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .coordonnees import Trouvaille, masquees
from .models import AlerteFraudeModel

logger = logging.getLogger('apps.securite')

SEUIL = 3
FENETRE = timedelta(days=30)


def signaler(utilisateur_id, contexte: str, objet_id, trouvailles: list[Trouvaille]) -> AlerteFraudeModel | None:
    if not trouvailles:
        return None
    alerte = AlerteFraudeModel.objects.create(
        utilisateur_id=utilisateur_id, contexte=contexte, objet_id=str(objet_id),
        types=sorted({t.type for t in trouvailles}), extraits=[t.valeur[:120] for t in trouvailles][:10],
        masquee=masquees(trouvailles),
    )
    nombre = AlerteFraudeModel.objects.filter(utilisateur_id=utilisateur_id, cree_le__gte=timezone.now() - FENETRE).count()
    if nombre == SEUIL:
        transaction.on_commit(lambda: _prevenir_admins(alerte, nombre))
    return alerte


def _prevenir_admins(alerte: AlerteFraudeModel, nombre: int) -> None:
    from apps.notifications.infrastructure.email.envoi import send_mail

    try:
        u = alerte.utilisateur
        admins = list(get_user_model().objects.filter(role='admin', is_active=True).values_list('email', flat=True)[:10])
        if not admins:
            return
        message = (
            f"{nombre} tentatives de contournement en 30 jours pour {u.first_name} {u.last_name} <{u.email}> ({u.get_role_display()}).\n\n"
            f"Dernière : {alerte.get_contexte_display().lower()}, {', '.join(alerte.types)}.\n\n"
            f"Examinez-les dans le back-office : {settings.FRONTEND_URL.rstrip('/')}/backoffice/anti-fraude\n"
        )
        send_mail(f"[Kwa-Ba] Anti-fraude : {u.email}", message, settings.DEFAULT_FROM_EMAIL, admins)
    except Exception:
        logger.exception("Alerte anti-fraude non envoyée")
