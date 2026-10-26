from abc import ABC, abstractmethod
from typing import Iterable, Set, Tuple
import uuid

Pair = Tuple[uuid.UUID, uuid.UUID]  # (hebergement_id, guest_id)


class BookingLookup(ABC):
    """Read access to bookings: does the traveller have a paid (confirmed) booking for this listing?

    Until they do, they stay anonymous to the host."""

    @abstractmethod
    def booked(self, pairs: Iterable[Pair]) -> Set[Pair]:
        pass


class EveryoneBooked(BookingLookup):
    """All identities visible (domain tests)."""

    def booked(self, pairs: Iterable[Pair]) -> Set[Pair]:
        return set(pairs)
