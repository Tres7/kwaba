"""Bookings given to the listings module (registered in hebergements at start-up)."""
from django.db.models import Q
from django.utils import timezone

from apps.hebergements.api import FournisseurReservations
from apps.paiements import api as paiements
from apps.users import api as users

from .models import ReservationModel


def _actives() -> Q:
    """Bookings that hold their dates: confirmed, or waiting for a non-expired payment.

    A pending booking without a deadline (created before online payment, or by hand) holds its dates for the
    payment delay after its creation, never forever.
    """
    maintenant = timezone.now()
    return (
        Q(status='confirmed')
        | Q(status='pending', expire_le__isnull=True, created_at__gt=maintenant - paiements.delai_paiement())
        | Q(status='pending', expire_le__gt=maintenant)
    )


def _sur_la_periode(hebergement_ids, debut, fin, exclure=None):
    qs = ReservationModel.objects.filter(_actives(), hebergement_id__in=list(hebergement_ids), check_in__lt=fin,
                                         check_out__gt=debut)
    return qs.exclude(pk=exclure) if exclure else qs


def actives(hebergement_ids, debut, fin, exclure=None) -> list[dict]:
    return list(_sur_la_periode(hebergement_ids, debut, fin, exclure)
                .values('id', 'hebergement_id', 'type_logement_id', 'check_in', 'check_out', 'nb_unites'))


def detail(hebergement_id, debut, fin) -> list[dict]:
    return [{
        'id': r.id, 'hebergement_id': r.hebergement_id, 'type_logement_id': r.type_logement_id, 'check_in': r.check_in,
        'check_out': r.check_out, 'nb_unites': r.nb_unites, 'reference': r.reference, 'statut': r.status,
        'voyageur': f"{r.guest.first_name} {r.guest.last_name}".strip(),
    } for r in users.attacher(_sur_la_periode([hebergement_id], debut, fin), 'guest')]


def sejour_paye_a_venir(hebergement_id) -> bool:
    return ReservationModel.objects.filter(hebergement_id=hebergement_id, status='confirmed',
                                           check_out__gte=timezone.localdate()).exists()


def annuler_en_attente(hebergement_id) -> list[dict]:
    en_attente = users.attacher(ReservationModel.objects.filter(hebergement_id=hebergement_id, status='pending'), 'guest')
    ReservationModel.objects.filter(pk__in=[r.pk for r in en_attente]).update(
        status='cancelled', annule_par='hote', annule_le=timezone.now(),
    )
    return [{'id': r.pk, 'email': r.guest.email, 'prenom': r.guest.first_name, 'check_in': r.check_in,
             'check_out': r.check_out} for r in en_attente]


def type_reserve(type_logement_id) -> bool:
    return ReservationModel.objects.filter(type_logement_id=type_logement_id).exists()


FOURNISSEUR = FournisseurReservations(
    actives=actives, detail=detail, sejour_paye_a_venir=sejour_paye_a_venir, annuler_en_attente=annuler_en_attente,
    type_reserve=type_reserve,
)
