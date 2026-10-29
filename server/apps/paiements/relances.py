"""Emails of a booking waiting for payment (listing, transfer, car rental).

The traveller has `PAIEMENT_EXPIRATION_MINUTES` (30 by default) to pay: the dates are held during that time.

1. right at booking: "to pay before HH:MM", with the payment link;
2. half way through, if they still have not paid: reminder;
3. after the automatic cancellation (worker): "cancelled for lack of payment", dates released.

The step reached is kept in `relance_paiement`: each email is sent only once, and a failed sending
is retried at the next pass of the worker. The confirmation (payment received) is still sent by notifications.py.
"""
import logging
from zoneinfo import ZoneInfo

from django.utils import formats, timezone

from .notifications import _envoyer, _fcfa
from .registre import PRODUITS
from .services import delai_paiement

logger = logging.getLogger('apps.paiements.relances')

AUCUN, ATTENTE, RAPPEL, ANNULATION = 0, 1, 2, 3
FUSEAU = ZoneInfo('Africa/Lome')


def _heure(moment) -> str:
    return formats.time_format(moment.astimezone(FUSEAU), 'H\\hi')


def _email(etape: int, ligne, decrire) -> None:
    objet = decrire(ligne)
    voyageur = objet['voyageur']
    contexte = {'prenom': voyageur.first_name, 'quoi': objet['quoi'], 'montant': _fcfa(objet['montant']),
                'url': objet['url']}
    if etape == ANNULATION:
        _envoyer('paiement_expire', "Réservation annulée : paiement non reçu", [voyageur.email], contexte)
        return
    contexte['avant'] = _heure(ligne.expire_le)
    contexte['minutes'] = max(1, int((ligne.expire_le - timezone.now()).total_seconds() // 60))
    if etape == ATTENTE:
        _envoyer('paiement_attente', f"Payez avant {contexte['avant']} pour confirmer votre réservation",
                 [voyageur.email], contexte)
    else:
        _envoyer('paiement_rappel', f"Plus que {contexte['minutes']} minutes pour payer votre réservation",
                 [voyageur.email], contexte)


def _avancer(qs, etape: int, decrire) -> int:
    envoyes = 0
    for ligne in qs[:50]:
        try:
            _email(etape, ligne, decrire)
        except Exception:
            logger.exception("Relance de paiement non envoyée pour %s %s (nouvel essai à la prochaine passe)",
                             type(ligne).__name__, ligne.pk)
            continue
        type(ligne).objects.filter(pk=ligne.pk).update(relance_paiement=etape)
        envoyes += 1
    return envoyes


def envoyer_relances() -> int:
    maintenant = timezone.now()
    mi_delai = delai_paiement() / 2
    total = 0
    for relance in (p.relance for p in PRODUITS.values() if p.relance):
        qs, statut, decrire = relance.requete(), relance.champ_statut, relance.decrire
        attente = qs.filter(**{statut: relance.en_attente}, expire_le__gt=maintenant)
        total += _avancer(attente.filter(relance_paiement=AUCUN), ATTENTE, decrire)
        # Reminder half way through; if the previous pass missed the waiting email, the reminder replaces it
        total += _avancer(attente.filter(relance_paiement__lt=RAPPEL, expire_le__lte=maintenant + mi_delai),
                          RAPPEL, decrire)
        # Cancelled for lack of payment: only if the traveller had been told they had to pay
        total += _avancer(qs.filter(**{statut: relance.annule, relance.champ_annule_par: 'expiration'},
                                    relance_paiement__in=(ATTENTE, RAPPEL)), ANNULATION, decrire)
    return total
