"""Alerts of the finance team, sent through the notifications module (notifications.api.send_mail) to the admins
who see the « Finances » section of the back-office (users.api). The finance role of FIN-13 will join them."""
import logging

from django.conf import settings
from django.template.loader import render_to_string

from apps.finance.application.ports import Alertes
from apps.notifications.api import send_mail
from apps.users import api as users

logger = logging.getLogger('apps.finance')

SECTION = 'finances'


def _envoyer(gabarit: str, sujet: str, contexte: dict) -> None:
    # Sent at once, not on commit: a refused movement usually rolls back the caller's transaction, and the alert
    # must leave anyway. An email that cannot leave never makes the money action fail.
    try:
        destinataires = users.emails_admins_section(SECTION)
        if not destinataires:
            logger.warning('Alerte finance %s : aucun administrateur ne voit la section Finances', gabarit)
            return
        send_mail(f'[Kwa-Ba Finance] {sujet}', render_to_string(f'emails/finance/{gabarit}.txt', contexte),
                  settings.DEFAULT_FROM_EMAIL, destinataires)
    except Exception:
        logger.exception('Alerte finance %s non envoyée', gabarit)


class EmailAlertes(Alertes):
    def mouvement_refuse(self, origine: str, raison: str) -> None:
        # The technical trace stays in the container logs, without amount (NFF-05)
        logger.error('Mouvement refusé par le grand livre (origine %s) : %s', origine, raison)
        _envoyer('mouvement_refuse', 'Mouvement refusé par le grand livre', {'origine': origine, 'raison': raison})

    def evenement_rejoue(self, mouvement_id: int, nature: str) -> None:
        logger.error('Événement externe déjà enregistré (ligne #%s, nature %s) rejoué avec un montant différent',
                     mouvement_id, nature)
        _envoyer('evenement_rejoue', 'Événement de paiement rejoué avec un autre montant',
                 {'mouvement_id': mouvement_id, 'nature': nature})
