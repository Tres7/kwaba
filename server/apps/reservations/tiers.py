"""Payment of a stay by a third party: the traveller asks someone else to pay their booking in full.

    the traveller creates a request: a secret link (24 h), which can also be opened to a Together trip
    the payer, signed in, sees the stay without anyone's contact details, then pays it at FedaPay or PayPal
    the payment is the payer's: their receipt, and the refunds if the stay is cancelled (on the means charged)

The dates stay held 30 minutes, as for any booking: the link does not lengthen the hold (a listing cannot be blocked
without paying). After that, the payment is accepted only if the units are still free, and paiement_recu checks again
when the money arrives (refunded in full otherwise).
"""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.hebergements import api as hebergements
from apps.paiements import api as paiements
from apps.users import api as users

from . import paiement
from .models import DemandePaiementModel, ReservationModel

DUREE_LIEN = timedelta(hours=24)


def _empreinte(jeton: str) -> str:
    return hashlib.sha256(jeton.encode()).hexdigest()


def _actives():
    return DemandePaiementModel.objects.filter(revoquee_le__isnull=True, expire_le__gt=timezone.now())


def demande_active(reservation) -> DemandePaiementModel | None:
    return _actives().filter(reservation=reservation).first()


def demande_par_jeton(jeton: str) -> DemandePaiementModel | None:
    """The request of a link, even expired or revoked (the page explains why it can no longer be paid)."""
    if not jeton or len(jeton) > 100:
        return None
    return DemandePaiementModel.objects.select_related('reservation').filter(empreinte_jeton=_empreinte(jeton)).first()


def _verifier_creation(reservation) -> None:
    if reservation.status != 'pending' or (reservation.expire_le and reservation.expire_le <= timezone.now()):
        raise paiements.PaiementErreur("Cette réservation n'attend plus de paiement : il est trop tard pour la faire payer par quelqu'un d'autre.")


def creer_lien(reservation) -> tuple[DemandePaiementModel, str]:
    """New secret link for the booking (the previous one stops working). Returns the request and the link's secret,
    which is never stored: it is shown once to the traveller."""
    _verifier_creation(reservation)
    jeton = secrets.token_urlsafe(32)
    with transaction.atomic():
        precedente = _actives().select_for_update().filter(reservation=reservation).first()
        _actives().filter(reservation=reservation).update(revoquee_le=timezone.now())
        demande = DemandePaiementModel.objects.create(
            reservation=reservation, empreinte_jeton=_empreinte(jeton), expire_le=timezone.now() + DUREE_LIEN,
            # Still open to the Together trip it was opened to
            voyage_id=precedente.voyage_id if precedente else None,
        )
    return demande, jeton


def ouvrir_au_groupe(reservation, voyage_id) -> DemandePaiementModel:
    """The members of the Together trip may pay the booking (the current request, or a new one without a link)."""
    _verifier_creation(reservation)
    with transaction.atomic():
        demande = _actives().select_for_update().filter(reservation=reservation).first()
        if demande:
            demande.voyage_id = voyage_id
            demande.save(update_fields=['voyage_id'])
            return demande
        return DemandePaiementModel.objects.create(
            reservation=reservation, empreinte_jeton=_empreinte(secrets.token_urlsafe(32)),
            expire_le=timezone.now() + DUREE_LIEN, voyage_id=voyage_id,
        )


def revoquer(reservation) -> int:
    return _actives().filter(reservation=reservation).update(revoquee_le=timezone.now())


def verifier(demande, payeur) -> ReservationModel:
    """The booking, if this person may pay it now; otherwise PaiementErreur with the reason, for them."""
    maintenant = timezone.now()
    if demande.revoquee_le or demande.expire_le <= maintenant:
        raise paiements.PaiementErreur("Ce lien de paiement n'est plus valable : demandez-en un nouveau à la personne qui a réservé.")
    r = ReservationModel.objects.get(pk=demande.reservation_id)
    if payeur.pk == r.guest_id:
        raise paiements.PaiementErreur("C'est votre réservation : payez-la depuis Mes réservations.")
    annonce = hebergements.fiche(r.hebergement_id, archivees=True)
    if not annonce or payeur.pk == annonce['host_id']:
        raise paiements.PaiementErreur("L'hôte ne peut pas payer une réservation de son propre logement.")
    if r.status == 'confirmed':
        raise paiements.PaiementErreur("Ce séjour est déjà payé.")
    if not (r.status == 'pending' or (r.status == 'cancelled' and r.annule_par == 'expiration')):
        raise paiements.PaiementErreur("Cette réservation a été annulée.")
    if r.check_in < timezone.localdate():
        raise paiements.PaiementErreur("La date d'arrivée est passée : ce séjour ne peut plus être payé.")
    if not (r.status == 'pending' and r.expire_le and r.expire_le > maintenant):
        # The dates are no longer held: payable only if they are still free
        if not hebergements.est_publiee(r.hebergement_id) or hebergements.conflit(
                r.hebergement_id, r.check_in, r.check_out, exclure=r.pk, type_logement_id=r.type_logement_id,
                nb=r.nb_unites or 1):
            raise paiements.PaiementErreur("Les dates ne sont plus disponibles : ce séjour ne peut plus être payé.")
    return r


def apercu(demande, payeur) -> dict:
    """What the payer sees: the stay and its price, the traveller's first name. Neither the address nor anyone's
    contact details (everything goes through the platform)."""
    r = ReservationModel.objects.get(pk=demande.reservation_id)
    annonce = hebergements.fiche(r.hebergement_id, archivees=True) or {}
    voyageur = users.compte(r.guest_id)
    try:
        verifier(demande, payeur)
        motif = ''
    except paiements.PaiementErreur as exc:
        motif = str(exc)
    return {
        'demande': str(demande.pk), 'reference': r.reference, 'voyageur': voyageur.first_name if voyageur else '',
        'hebergement': {'name': annonce.get('name', ''), 'city': annonce.get('city', ''),
                        'image_url': annonce.get('image_url', ''), 'type': annonce.get('type_libelle', '')},
        'check_in': r.check_in, 'check_out': r.check_out, 'nuits': r.nights, 'voyageurs': r.guests_count,
        'total': paiements.montants_de(r).total, 'expire_le': demande.expire_le,
        'payable': not motif, 'motif': motif,
    }


def payer(demande, payeur, moyen: str) -> str:
    """Starts the payment of the stay by the payer; returns the address of the provider's payment page."""
    r = verifier(demande, payeur)
    return paiement.demarrer_paiement(r, moyen, payeur=payeur,
                                      url_retour=f"{settings.FRONTEND_URL}/payer/retour/{demande.pk}")


def statut_pour_payeur(demande, payeur) -> dict | None:
    """Return page of the payer: status of the payment they started (None if they never started one)."""
    r = demande.reservation
    if paiements.statut_paiement_de('reservation', r.pk, payeur.pk) is None:
        return None
    if paiements.synchroniser_dernier_paiement('reservation', r.pk):
        r.refresh_from_db()
    return {'reservation': r.status, 'paiement': paiements.statut_paiement_de('reservation', r.pk, payeur.pk),
            'voyageur': getattr(users.compte(r.guest_id), 'first_name', '')}


# --- Together: the members of a trip pay the booking shared with it ---------------------------------------------

def demande_du_groupe(reservation_id, voyage_id) -> DemandePaiementModel | None:
    return _actives().filter(reservation_id=reservation_id, voyage_id=voyage_id).first()


def demandes_des_groupes(reservation_ids, voyage_id) -> set:
    """Bookings among these that the trip's members are asked to pay."""
    return set(_actives().filter(reservation_id__in=list(reservation_ids), voyage_id=voyage_id)
               .values_list('reservation_id', flat=True))
