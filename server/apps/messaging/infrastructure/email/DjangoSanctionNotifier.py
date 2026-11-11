import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.messaging.application.ports.SanctionNotifier import SanctionNotifier
from apps.messaging.domain.entities.Sanction import CONTEST_ACCEPTED, Sanction
from apps.messaging.domain.services.SanctionLadder import (
    ADMIN_DECISION, FORMAL_WARNING, LONG_SUSPENSION, REMINDER, SHORT_SUSPENSION,
)
from apps.users import api as users

logger = logging.getLogger('apps.messaging')

CATEGORIES = {'insult': 'insulte', 'hate': 'propos haineux', 'threat': 'menace', 'harassment': 'harcèlement',
              'spam': 'spam', 'scam': 'arnaque', 'other': 'non-respect des règles'}

RULES = ("La messagerie Kwa-Ba sert à préparer les séjours. Les insultes, propos haineux, menaces et le harcèlement "
         "y sont interdits (voir nos conditions générales d'utilisation).")

SUBJECTS = {
    REMINDER: "Rappel des règles de la messagerie",
    FORMAL_WARNING: "Avertissement : règles de la messagerie",
    SHORT_SUSPENSION: "Votre messagerie est suspendue",
    LONG_SUSPENSION: "Votre messagerie est suspendue",
    ADMIN_DECISION: "Votre compte est en cours d'examen",
}


def _date(value) -> str:
    return f"{timezone.localtime(value):%d/%m/%Y à %H:%M}"


def _body(sanction: Sanction) -> str:
    reason = CATEGORIES.get(sanction.category, CATEGORIES['other'])
    opening = f"Un de vos messages a été signalé, puis jugé contraire aux règles par notre équipe (motif : {reason})."
    if sanction.step == REMINDER:
        detail = "Merci de rester courtois dans vos échanges."
    elif sanction.step == FORMAL_WARNING:
        detail = ("Ce n'est pas la première fois. Ceci est un avertissement formel : en cas de nouveau message "
                  "contraire aux règles, votre messagerie sera suspendue.")
    elif sanction.step in (SHORT_SUSPENSION, LONG_SUSPENSION):
        detail = (f"Votre messagerie est suspendue jusqu'au {_date(sanction.ends_at)} (heure UTC). Vous pouvez lire "
                  "vos conversations, mais pas écrire.")
    else:
        detail = ("Après une suspension récente, un nouveau message a été jugé contraire aux règles. Votre dossier est "
                  "transmis à l'équipe Kwa-Ba, qui décidera d'une éventuelle suspension de votre compte.")
    contest = (f"Vous pouvez contester cette décision pendant {settings.MODERATION['CONTEST_DAYS']} jours depuis votre messagerie : "
               f"{settings.FRONTEND_URL.rstrip('/')}/messages")
    return f"Bonjour,\n\n{opening}\n\n{detail}\n\n{RULES}\n\n{contest}\n\nL'équipe Kwa-Ba\n"


def _send(user_id, subject: str, body: str) -> None:
    from apps.notifications.api import send_mail

    try:
        account = users.compte(user_id)
        if account and account.email:
            send_mail(f"[Kwa-Ba] {subject}", body, settings.DEFAULT_FROM_EMAIL, [account.email])
    except Exception:
        logger.exception("Email de modération non envoyé")


class DjangoSanctionNotifier(SanctionNotifier):

    def sanction_applied(self, sanction: Sanction) -> None:
        subject, body = SUBJECTS[sanction.step], _body(sanction)
        transaction.on_commit(lambda: _send(sanction.user_id, subject, body))

    def contest_reviewed(self, sanction: Sanction) -> None:
        if sanction.contest_status == CONTEST_ACCEPTED:
            subject = "Votre contestation est acceptée"
            body = ("Bonjour,\n\nAprès examen, votre contestation est acceptée : la sanction est annulée et ne compte "
                    "plus dans votre historique.\n\nL'équipe Kwa-Ba\n")
        else:
            subject = "Votre contestation est rejetée"
            body = ("Bonjour,\n\nAprès examen par un membre de l'équipe, votre contestation est rejetée : la sanction "
                    f"est maintenue.\n\n{RULES}\n\nL'équipe Kwa-Ba\n")
        transaction.on_commit(lambda: _send(sanction.user_id, subject, body))
