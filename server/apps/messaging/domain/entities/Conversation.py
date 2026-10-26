from dataclasses import dataclass, field
import datetime
import uuid

from apps.messaging.domain.exceptions import (
    CannotContactOwnHebergementException,
    NotParticipantException,
)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


@dataclass
class Conversation:
    """Thread between a traveller (guest) and the host of a listing.

    Each participant has a read cursor: the id of the last message they read.
    Their unread messages are those of the other participant whose id is greater than this cursor.
    """
    hebergement_id: uuid.UUID
    guest_id: uuid.UUID
    host_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    guest_last_read_id: int = 0
    host_last_read_id: int = 0
    created_at: datetime.datetime = field(default_factory=_now)
    last_message_at: datetime.datetime = field(default_factory=_now)

    @staticmethod
    def start(hebergement_id: uuid.UUID, guest_id: uuid.UUID, host_id: uuid.UUID) -> 'Conversation':
        if guest_id == host_id:
            raise CannotContactOwnHebergementException(str(hebergement_id))
        return Conversation(hebergement_id=hebergement_id, guest_id=guest_id, host_id=host_id)

    def is_participant(self, user_id: uuid.UUID) -> bool:
        return user_id in (self.guest_id, self.host_id)

    def role_of(self, user_id: uuid.UUID) -> str:
        self._ensure_participant(user_id)
        return 'guest' if user_id == self.guest_id else 'host'

    def other_participant(self, user_id: uuid.UUID) -> uuid.UUID:
        self._ensure_participant(user_id)
        return self.host_id if user_id == self.guest_id else self.guest_id

    def last_read_id_for(self, user_id: uuid.UUID) -> int:
        self._ensure_participant(user_id)
        return self.guest_last_read_id if user_id == self.guest_id else self.host_last_read_id

    def mark_read(self, user_id: uuid.UUID, message_id: int) -> None:
        """Moves the read cursor forward. It never goes back."""
        self._ensure_participant(user_id)
        if user_id == self.guest_id:
            self.guest_last_read_id = max(self.guest_last_read_id, message_id)
        else:
            self.host_last_read_id = max(self.host_last_read_id, message_id)

    def record_message(self, sender_id: uuid.UUID, message_id: int, sent_at: datetime.datetime) -> None:
        """A sent message counts as read by its sender."""
        self.mark_read(sender_id, message_id)
        self.last_message_at = sent_at

    def _ensure_participant(self, user_id: uuid.UUID) -> None:
        if not self.is_participant(user_id):
            raise NotParticipantException(str(self.id))
