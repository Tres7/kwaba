from abc import ABC, abstractmethod
from typing import Optional

from apps.messaging.application.events.DomainEvent import DomainEvent


class EventPublisher(ABC):

    @abstractmethod
    def publish(self, event: DomainEvent, message_id: Optional[str] = None) -> None:
        """message_id lets the consumer deduplicate (at-least-once delivery)."""
        pass
