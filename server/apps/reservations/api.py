import uuid
from collections.abc import Iterable

from .models import ReservationModel


def appartient_au_voyageur(reservation_id: uuid.UUID, voyageur_id: uuid.UUID) -> bool:
    return ReservationModel.objects.filter(pk=reservation_id, guest_id=voyageur_id).exists()


def resumes(reservation_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, dict]:
    return {r.id: {
        'id': r.id, 'reference': r.reference, 'hebergement_id': r.hebergement_id, 'voyageur_id': r.guest_id,
        'check_in': r.check_in, 'check_out': r.check_out, 'voyageurs': r.guests_count, 'statut': r.status,
        'total': r.total_price,
    } for r in ReservationModel.objects.filter(pk__in=list(reservation_ids))}
