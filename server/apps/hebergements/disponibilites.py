"""Availability of an establishment and of its unit types (stock night by night: see stock.py).

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


def verrouiller_types(type_ids) -> None:
    """Locks unit types until the end of the current transaction (booking, payment confirmation, closure).

    A booking locks only its type: the other types of the same hotel stay bookable at the same time. A closure
    locks every type of the establishment. Always in the same order (by id), so that two locks never deadlock.
    """
    from .models import TypeLogementModel
    list(TypeLogementModel.objects.select_for_update().filter(pk__in=list(type_ids)).order_by('pk').values_list('pk', flat=True))


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


def _types(hebergement_id, type_logement=None) -> list:
    """The unit types concerned: the given one, or all the active types of the establishment."""
    from .models import TypeLogementModel
    from .types_logement import type_par_defaut_id
    if type_logement is not None:
        return [type_logement]
    actifs = list(TypeLogementModel.objects.filter(hebergement_id=hebergement_id, actif=True))
    return actifs or [TypeLogementModel.objects.get(pk=type_par_defaut_id(hebergement_id))]


def est_disponible(hebergement_id, debut: date, fin: date) -> bool:
    """At least one unit of one type of the establishment is free over the whole period."""
    from .stock import Occupation
    types = _types(hebergement_id)
    occupation = Occupation(types, debut, fin)
    return any(occupation.restantes(t.id) >= 1 for t in types)


def conflit(hebergement_id, debut: date, fin: date, exclure=None, type_logement=None, nb: int = 1) -> str | None:
    """Explains why `nb` units of the type (the establishment's default type if none) cannot be booked over the
    period (message for the traveller), or None.

    `exclure`: id of a booking to ignore (the one being confirmed).
    """
    from .stock import Occupation
    from .types_logement import type_par_defaut_id
    if type_logement is None:
        from .models import TypeLogementModel
        type_logement = TypeLogementModel.objects.get(pk=type_par_defaut_id(hebergement_id))
    occupation = Occupation([type_logement], debut, fin, exclure)
    if occupation.ferme(type_logement.id):
        return "L'hôte a fermé ces dates à la réservation."
    restantes = occupation.restantes(type_logement.id)
    if restantes >= nb:
        return None
    if restantes == 0:
        return "Ces dates sont déjà réservées pour cet hébergement."
    return f"Il ne reste que {restantes} logement{'s' if restantes > 1 else ''} de ce type disponible{'s' if restantes > 1 else ''} à ces dates."


def periodes_indisponibles(hebergement_id, debut: date, fin: date, detail: bool = False, type_logement=None) -> list[dict]:
    """Taken periods over [debut, fin).

    Host view (detail): every booking and closure. Public view: the nights when nothing can be booked (no unit left
    of the given type, or of any type of the establishment), merged into periods, without any information on why.
    """
    if detail:
        periodes = []
        for r in _reservations(hebergement_id, debut, fin).select_related('guest', 'type_logement'):
            periodes.append({'debut': r.check_in, 'fin': r.check_out, 'type': 'reservation', 'id': str(r.id),
                             'reference': r.reference, 'voyageur': f"{r.guest.first_name} {r.guest.last_name}".strip(),
                             'statut': r.status, 'nb_unites': r.nb_unites,
                             'type_logement': r.type_logement.nom if r.type_logement else None})
        for b in _blocages(hebergement_id, debut, fin).select_related('type_logement'):
            periodes.append({'debut': b.debut, 'fin': b.fin, 'type': 'blocage', 'id': str(b.id), 'motif': b.motif,
                             'type_logement': b.type_logement.nom if b.type_logement else None})
        periodes.sort(key=lambda p: p['debut'])
        return periodes

    from .stock import Occupation, nuits
    types = _types(hebergement_id, type_logement)
    occupation = Occupation(types, debut, fin)
    completes = [n for n in nuits(debut, fin) if all(occupation.restantes_nuit(t.id, n) == 0 for t in types)]
    # Consecutive full nights -> periods [first night, day after the last one)
    fusion = []
    for n in completes:
        if fusion and fusion[-1]['fin'] == n:
            fusion[-1]['fin'] = n + timedelta(days=1)
        else:
            fusion.append({'debut': n, 'fin': n + timedelta(days=1)})
    return fusion
