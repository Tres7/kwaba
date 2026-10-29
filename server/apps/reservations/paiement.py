"""Stays as a product paid online (registered in paiements at start-up): starting the payment, confirming the stay
once paid, cancelling it, releasing the dates of the stays not paid in time.

    "pending" booking (dates held 30 min)
        → successful payment → "confirmed" booking + payout to the host scheduled (arrival + 24 h)
    cancellation → refund of the traveller according to the scale, payout reduced or cancelled
"""
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import formats, timezone

from apps.hebergements import api as hebergements
from apps.paiements import api as paiements
from apps.paiements.api import ProduitPaye, Relance

from .models import ReservationModel


def _annonce(r) -> dict:
    return hebergements.fiche(r.hebergement_id, archivees=True)


def demarrer_paiement(reservation, moyen: str = 'mobile_money') -> str:
    """Payment of a listing booking: returns the address of the payment page."""
    if moyen not in paiements.moyens_actifs():
        raise paiements.PaiementErreur("Ce moyen de paiement n'est pas disponible.")
    if reservation.status != 'pending':
        raise paiements.PaiementErreur("Cette réservation n'attend pas de paiement.")
    if reservation.expire_le and reservation.expire_le <= timezone.now():
        raise paiements.PaiementErreur("Le délai de paiement est dépassé : les dates ont été libérées. Refaites la réservation.")

    if reservation.payment_method != moyen:
        reservation.payment_method = moyen
        reservation.save(update_fields=['payment_method'])
    return paiements.creer_paiement(
        type_objet='reservation', objet_id=reservation.id, montant=paiements.montants_de(reservation).total,
        moyen=moyen, voyageur=reservation.guest,
        description=f"Kwa-Ba {reservation.reference}, {_annonce(reservation)['name']}",
        url_retour=f"{settings.FRONTEND_URL}/reservation/paiement/{reservation.id}",
    )


def paiement_recu(paiement):
    """Called by apps.paiements, in its transaction, when the payment of a stay succeeds."""
    reservation = ReservationModel.objects.select_for_update().get(pk=paiement.reservation_id)
    if paiements.autre_paiement_reussi('reservation', reservation.pk, paiement):
        paiements.rembourser(paiement, paiement.montant, "Paiement reçu en double")
        return
    if reservation.status == 'cancelled' and reservation.annule_par != 'expiration':
        paiements.rembourser(paiement, paiement.montant, "Réservation annulée avant la confirmation du paiement")
        return
    # Payment arriving after the expiry: confirmed if the units are still free.
    # Unit-type lock: a simultaneous booking cannot take them in the meantime.
    if reservation.type_logement_id:
        hebergements.verrouiller_types([reservation.type_logement_id])
    else:
        hebergements.verrouiller(reservation.hebergement_id)
    if hebergements.conflit(reservation.hebergement_id, reservation.check_in, reservation.check_out, exclure=reservation.pk,
                            type_logement_id=reservation.type_logement_id, nb=reservation.nb_unites or 1):
        paiements.rembourser(paiement, paiement.montant, "Dates plus disponibles au moment du paiement")
        reservation.status, reservation.annule_par = 'cancelled', 'plateforme'
        reservation.annule_le = timezone.now()
        reservation.save(update_fields=['status', 'annule_par', 'annule_le'])
        return

    reservation.status = 'confirmed'
    reservation.expire_le = None
    reservation.annule_par, reservation.annule_le = '', None
    reservation.save(update_fields=['status', 'expire_le', 'annule_par', 'annule_le'])
    paiements.planifier_versement_hote(reservation)


def annuler(reservation, par: str) -> int:
    """Cancels the booking. `par`: voyageur, hote or plateforme. Returns the amount refunded to the traveller."""
    with transaction.atomic():
        reservation = ReservationModel.objects.select_for_update().get(pk=reservation.pk)
        if reservation.status == 'cancelled':
            raise paiements.PaiementErreur("Cette réservation est déjà annulée.")
        rembourse = paiements.annuler_paiement_reservation(reservation, par)
        reservation.status = 'cancelled'
        reservation.annule_par = par
        reservation.annule_le = timezone.now()
        reservation.save(update_fields=['status', 'annule_par', 'annule_le'])
        hebergements.signaler_liberation(reservation.hebergement_id, reservation.check_in, reservation.check_out)
        return rembourse


def expirer() -> int:
    """Releases the dates of the bookings not paid in time (after a last check)."""
    expirees = 0
    maintenant = timezone.now()
    a_expirer = Q(expire_le__lte=maintenant) | Q(expire_le__isnull=True, created_at__lte=maintenant - paiements.delai_paiement())
    for reservation in ReservationModel.objects.filter(a_expirer, status='pending'):
        paiements.synchroniser_paiements_en_attente('reservation', reservation.pk)
        if ReservationModel.objects.filter(pk=reservation.pk, status='pending').update(
            status='cancelled', annule_par='expiration', annule_le=maintenant,
        ):
            expirees += 1
            hebergements.signaler_liberation(reservation.hebergement_id, reservation.check_in, reservation.check_out)
    return expirees


def passe() -> dict:
    # After the expiries of this pass: the dates they freed are checked at once
    return {'reservations_expirees': expirer(), **hebergements.passe_alertes()}


def decrire(reservation_id) -> dict | None:
    r = ReservationModel.objects.filter(pk=reservation_id).select_related('guest').first()
    if not r:
        return None
    return {'payeur': r.guest, 'reference': r.reference, 'libelle': _annonce(r)['name'], 'moyen': r.payment_method}


def _decrire_relance(r) -> dict:
    annonce = _annonce(r)
    return {'voyageur': r.guest, 'montant': int(r.total_price),
            'url': f"{settings.FRONTEND_URL}/reservation/paiement/{r.id}",
            'quoi': f"votre séjour « {annonce['name']} » ({annonce['city']}), "
                    f"du {formats.date_format(r.check_in, 'j F')} au {formats.date_format(r.check_out, 'j F Y')}"}


PRODUIT_PAYE = ProduitPaye(
    type='reservation',
    decrire=decrire,
    paiement_recu=paiement_recu,
    passe=passe,
    relance=Relance(
        requete=lambda: ReservationModel.objects.select_related('guest'), champ_statut='status', en_attente='pending',
        annule='cancelled', champ_annule_par='annule_par', decrire=_decrire_relance,
    ),
)
