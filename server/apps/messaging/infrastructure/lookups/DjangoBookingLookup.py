import uuid
from typing import Iterable, Optional, Set

from apps.messaging.application.ports.BookingLookup import BookingLookup, Pair
from apps.reservations import api as reservations


class DjangoBookingLookup(BookingLookup):
    """Only contact point of messaging with bookings. Confirmed = paid (payment required in production)."""

    def booked(self, pairs: Iterable[Pair]) -> Set[Pair]:
        return reservations.paires_confirmees(pairs)

    def confirmed_for_host(self, reservation_id: uuid.UUID, host_id: uuid.UUID) -> Optional[Pair]:
        return reservations.confirmee_pour_hote(reservation_id, host_id)
