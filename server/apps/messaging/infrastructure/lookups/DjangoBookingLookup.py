from typing import Iterable, Set

from django.db.models import Q

from apps.messaging.application.ports.BookingLookup import BookingLookup, Pair


class DjangoBookingLookup(BookingLookup):
    """Only contact point of messaging with bookings. Confirmed = paid (payment required in production)."""

    def booked(self, pairs: Iterable[Pair]) -> Set[Pair]:
        pairs = set(pairs)
        if not pairs:
            return set()
        from apps.reservations.models import ReservationModel  # local import: reservations depends on hebergements

        condition = Q()
        for hebergement_id, guest_id in pairs:
            condition |= Q(hebergement_id=hebergement_id, guest_id=guest_id)
        rows = ReservationModel.objects.filter(condition, status='confirmed').values_list('hebergement_id', 'guest_id')
        return set(rows) & pairs
