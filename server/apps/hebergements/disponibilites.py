"""Availability of a listing: a night is taken if an active booking or a host block covers it.

Shared convention: a period [debut, fin) covers the nights from debut to fin - 1;
the `fin` day (departure) stays free for a new arrival.
"""
from datetime import date, timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import BlocageModel, HebergementModel


def verrouiller(hebergement_id) -> None:
    """Locks the listing until the end of the current transaction.

    To call before conflit() or a_des_reservations() as soon as the decision leads to a write
    (booking, payment confirmation, block): without a lock, two simultaneous requests both see
    the dates free and book the same nights. Raises an error outside a transaction.
    """
    list(HebergementModel.objects.select_for_update().filter(pk=hebergement_id).values_list('pk', flat=True))


def filtre_actives(prefixe: str = ''):
    """Bookings that hold their dates: confirmed, or waiting for a non-expired payment.

    A pending booking without a deadline (created before online payment, or by hand) holds its dates for the
    payment delay after its creation, never forever.
    """
    p = prefixe
    maintenant = timezone.now()
    return (
        Q(**{f'{p}status': 'confirmed'})
        | Q(**{f'{p}status': 'pending', f'{p}expire_le__isnull': True, f'{p}created_at__gt': maintenant - delai_paiement()})
        | Q(**{f'{p}status': 'pending', f'{p}expire_le__gt': maintenant})
    )


def delai_paiement() -> timedelta:
    """Time given to pay a booking (same setting as apps.paiements.services.delai_paiement)."""
    return timedelta(minutes=settings.FEDAPAY['EXPIRATION_MINUTES'])


def _reservations(hebergement_id, debut: date, fin: date, exclure=None):
    from apps.reservations.models import ReservationModel  # local import: avoids a circular import
    qs = ReservationModel.objects.filter(
        filtre_actives(),
        hebergement_id=hebergement_id,
        check_in__lt=fin,
        check_out__gt=debut,
    )
    return qs.exclude(pk=exclure) if exclure else qs


def _blocages(hebergement_id, debut: date, fin: date):
    return BlocageModel.objects.filter(hebergement_id=hebergement_id, debut__lt=fin, fin__gt=debut)


def a_des_reservations(hebergement_id, debut: date, fin: date) -> bool:
    return _reservations(hebergement_id, debut, fin).exists()


def est_disponible(hebergement_id, debut: date, fin: date) -> bool:
    return not _reservations(hebergement_id, debut, fin).exists() and not _blocages(hebergement_id, debut, fin).exists()


def conflit(hebergement_id, debut: date, fin: date, exclure=None) -> str | None:
    """Explains why the period is not free (message for the traveller), or None.

    `exclure`: id of a booking to ignore (the one being confirmed).
    """
    if _reservations(hebergement_id, debut, fin, exclure).exists():
        return "Ces dates sont déjà réservées pour cet hébergement."
    if _blocages(hebergement_id, debut, fin).exists():
        return "L'hôte a fermé ces dates à la réservation."
    return None


def periodes_indisponibles(hebergement_id, debut: date, fin: date, detail: bool = False) -> list[dict]:
    """Taken periods over [debut, fin). In public mode, merged and without any information on their origin."""
    periodes = []
    for r in _reservations(hebergement_id, debut, fin).select_related('guest'):
        p = {'debut': r.check_in, 'fin': r.check_out}
        if detail:
            p.update(type='reservation', id=str(r.id), reference=r.reference,
                     voyageur=f"{r.guest.first_name} {r.guest.last_name}".strip(), statut=r.status)
        periodes.append(p)
    for b in _blocages(hebergement_id, debut, fin):
        p = {'debut': b.debut, 'fin': b.fin}
        if detail:
            p.update(type='blocage', id=str(b.id), motif=b.motif)
        periodes.append(p)

    periodes.sort(key=lambda p: p['debut'])
    if detail:
        return periodes

    # Merges touching periods: the traveller only sees "free / taken"
    fusion = []
    for p in periodes:
        if fusion and p['debut'] <= fusion[-1]['fin']:
            fusion[-1]['fin'] = max(fusion[-1]['fin'], p['fin'])
        else:
            fusion.append(dict(p))
    return fusion
