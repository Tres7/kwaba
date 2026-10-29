"""Emails of a booking waiting for payment (listing, transfer, car rental).

The traveller has `PAIEMENT_EXPIRATION_MINUTES` (30 by default) to pay: the dates are held during that time.

1. right at booking: "to pay before HH:MM", with the payment link;
2. half way through, if they still have not paid: reminder;
3. after the automatic cancellation (worker): "cancelled for lack of payment", dates released.

The step reached is kept in `relance_paiement`: each email is sent only once, and a failed sending
is retried at the next pass of the worker. The confirmation (payment received) is still sent by notifications.py.
"""
import logging
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import formats, timezone

from . import tarifs
from .notifications import _envoyer, _fcfa
from .services import delai_paiement

logger = logging.getLogger('apps.paiements.relances')

AUCUN, ATTENTE, RAPPEL, ANNULATION = 0, 1, 2, 3
FUSEAU = ZoneInfo('Africa/Lome')


@dataclass
class Objet:
    """What the emails say about a booking, whatever its type."""
    voyageur: object
    quoi: str
    montant: int
    url: str


def _heure(moment) -> str:
    return formats.time_format(moment.astimezone(FUSEAU), 'H\\hi')


def _reservation(r) -> Objet:
    annonce = tarifs._annonce(r)
    return Objet(r.guest, f"votre séjour « {annonce['name']} » ({annonce['city']}), "
                          f"du {formats.date_format(r.check_in, 'j F')} au {formats.date_format(r.check_out, 'j F Y')}",
                 int(r.total_price), f"{settings.FRONTEND_URL}/reservation/paiement/{r.id}")


def _transfert(t) -> Objet:
    return Objet(t.voyageur, f"votre transfert depuis l'aéroport de {t.aeroport.ville} "
                             f"({formats.date_format(t.arrivee.astimezone(FUSEAU), 'j F Y')})",
                 t.prix, f"{settings.FRONTEND_URL}/transfert/{t.id}")


def _location(loc) -> Objet:
    return Objet(loc.voyageur, f"votre location « {loc.libelle} », "
                               f"du {formats.date_format(loc.debut.astimezone(FUSEAU), 'j F')} "
                               f"au {formats.date_format(loc.fin.astimezone(FUSEAU), 'j F Y')}",
                 loc.prix, f"{settings.FRONTEND_URL}/location/{loc.id}")


def _sources():
    """(query, status field, pending status, cancelled status, "cancelled by" field, description)."""
    from apps.locations.models import LocationModel
    from apps.reservations.models import ReservationModel
    from apps.transferts.models import TransfertModel

    return [
        (ReservationModel.objects.select_related('guest'), 'status', 'pending', 'cancelled',
         'annule_par', _reservation),
        (TransfertModel.objects.select_related('voyageur', 'aeroport'), 'statut', 'en_attente_paiement', 'annule',
         'annule_par', _transfert),
        (LocationModel.objects.select_related('voyageur', 'categorie'), 'statut', 'en_attente_paiement', 'annulee',
         'annulee_par', _location),
    ]


def _email(etape: int, ligne, decrire) -> None:
    objet = decrire(ligne)
    contexte = {'prenom': objet.voyageur.first_name, 'quoi': objet.quoi, 'montant': _fcfa(objet.montant),
                'url': objet.url}
    if etape == ANNULATION:
        _envoyer('paiement_expire', "Réservation annulée : paiement non reçu", [objet.voyageur.email], contexte)
        return
    contexte['avant'] = _heure(ligne.expire_le)
    contexte['minutes'] = max(1, int((ligne.expire_le - timezone.now()).total_seconds() // 60))
    if etape == ATTENTE:
        _envoyer('paiement_attente', f"Payez avant {contexte['avant']} pour confirmer votre réservation",
                 [objet.voyageur.email], contexte)
    else:
        _envoyer('paiement_rappel', f"Plus que {contexte['minutes']} minutes pour payer votre réservation",
                 [objet.voyageur.email], contexte)


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
    for qs, statut, en_attente, annule, annule_par, decrire in _sources():
        attente = qs.filter(**{statut: en_attente}, expire_le__gt=maintenant)
        total += _avancer(attente.filter(relance_paiement=AUCUN), ATTENTE, decrire)
        # Reminder half way through; if the previous pass missed the waiting email, the reminder replaces it
        total += _avancer(attente.filter(relance_paiement__lt=RAPPEL, expire_le__lte=maintenant + mi_delai),
                          RAPPEL, decrire)
        # Cancelled for lack of payment: only if the traveller had been told they had to pay
        total += _avancer(qs.filter(**{statut: annule, annule_par: 'expiration'},
                                    relance_paiement__in=(ATTENTE, RAPPEL)), ANNULATION, decrire)
    return total
