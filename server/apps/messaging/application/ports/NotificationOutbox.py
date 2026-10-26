from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime
from typing import Optional
import uuid


@dataclass
class OutboxEntry:
    id: int
    event_type: str
    conversation_id: uuid.UUID
    message_id: int
    recipient_id: uuid.UUID
    payload: dict
    attempts: int


class NotificationOutbox(ABC):
    """Notifications to publish, written in the same transaction as the message (outbox pattern).

    Statuses: pending (to publish), sent (published), skipped (no longer needed).
    """

    @abstractmethod
    def schedule(
        self,
        event_type: str,
        conversation_id: uuid.UUID,
        message_id: int,
        recipient_id: uuid.UUID,
        payload: dict,
        available_at: datetime.datetime,
    ) -> None:
        pass

    @abstractmethod
    def claim_next_due(self, now: datetime.datetime) -> Optional[OutboxEntry]:
        """Locks the next due pending row, skipping those already locked
        by another relay (skip locked). To call inside a transaction."""
        pass

    @abstractmethod
    def mark_sent(self, entry_id: int, now: datetime.datetime) -> None:
        pass

    @abstractmethod
    def mark_skipped(self, entry_id: int, now: datetime.datetime, reason: str) -> None:
        pass

    @abstractmethod
    def postpone(self, entry_id: int, available_at: datetime.datetime) -> None:
        """Postpones without failure (cap reached): the attempt counter does not move."""
        pass

    @abstractmethod
    def record_failure(self, entry_id: int, available_at: datetime.datetime, error: str) -> int:
        """Increments the attempts, keeps the error, postpones the row. Returns the new number of attempts."""
        pass

    @abstractmethod
    def sent_since(self, recipient_id: uuid.UUID, since: datetime.datetime) -> list:
        """Sending dates (ascending) of the notifications already published for this recipient since `since`."""
        pass

    @abstractmethod
    def purge_processed_before(self, before: datetime.datetime) -> int:
        """Deletes the sent/skipped rows processed before `before`. Returns the number deleted."""
        pass
