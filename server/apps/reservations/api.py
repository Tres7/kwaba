import uuid
from collections.abc import Iterable
from datetime import date

from django.db.models import Q
from django.utils import timezone

from apps.paiements import api as paiements

from .models import ReservationModel


def appartient_au_voyageur(reservation_id: uuid.UUID, voyageur_id: uuid.UUID) -> bool:
    return ReservationModel.objects.filter(pk=reservation_id, guest_id=voyageur_id).exists()


def resumes(reservation_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, dict]:
    return {r.id: {
        'id': r.id, 'reference': r.reference, 'hebergement_id': r.hebergement_id, 'voyageur_id': r.guest_id,
        'check_in': r.check_in, 'check_out': r.check_out, 'voyageurs': r.guests_count, 'statut': r.status,
        'total': r.total_price,
    } for r in ReservationModel.objects.filter(pk__in=list(reservation_ids))}


def paires_confirmees(paires: Iterable[tuple[uuid.UUID, uuid.UUID]]) -> set[tuple[uuid.UUID, uuid.UUID]]:
    paires = set(paires)
    if not paires:
        return set()
    condition = Q()
    for hebergement_id, voyageur_id in paires:
        condition |= Q(hebergement_id=hebergement_id, guest_id=voyageur_id)
    return set(ReservationModel.objects.filter(condition, status='confirmed').values_list('hebergement_id', 'guest_id')) & paires


def confirmee_pour_hote(reservation_id: uuid.UUID, hote_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID] | None:
    return (ReservationModel.objects.filter(pk=reservation_id, hebergement__host_id=hote_id, status='confirmed')
            .values_list('hebergement_id', 'guest_id').first())


def sejours_termines(voyageur_id: uuid.UUID, depart_depuis: date, depart_jusqu_a: date) -> list[dict]:
    return [{
        'id': r.id, 'hebergement_id': r.hebergement_id, 'check_in': r.check_in, 'check_out': r.check_out,
    } for r in ReservationModel.objects.filter(guest_id=voyageur_id, status='confirmed', check_out__lte=depart_jusqu_a,
                                               check_out__gte=depart_depuis).order_by('-check_out')]


def reduire_frais_pack_sejour(reservation_id: uuid.UUID, voyageur_id: uuid.UUID) -> tuple[int, str]:
    """Stay Pack + Driver: an upcoming paid stay of this traveller gets service fees lowered to the reduced rate.
    Returns (amount to refund, booking reference); (0, '') if the stay is not eligible. To call in a transaction."""
    r = ReservationModel.objects.select_for_update().filter(pk=reservation_id).first()
    if not r or r.guest_id != voyageur_id or r.status != 'confirmed' or r.check_in <= timezone.localdate():
        return 0, ''
    if r.prix_nuits is None or r.frais_service is None:
        return 0, ''
    nouveaux_frais = paiements.frais_reduits_sejour(r.prix_nuits)
    ecart = r.frais_service - nouveaux_frais
    if ecart <= 0:
        return 0, ''
    r.frais_service, r.total_price = nouveaux_frais, r.prix_nuits + nouveaux_frais
    r.save(update_fields=['frais_service', 'total_price'])
    return ecart, r.reference
