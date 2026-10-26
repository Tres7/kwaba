# Contract of the event consumed by the notifications module.
# It is self-contained: notifications never needs to read the messaging data again.
from dataclasses import dataclass

from apps.messaging.application.events.DomainEvent import DomainEvent


@dataclass
class NewMessageEmailRequested(DomainEvent):
    outbox_id: int            # deduplication id (at-least-once delivery)
    conversation_id: str
    recipient_email: str
    recipient_first_name: str
    sender_first_name: str
    hebergement_name: str
    message_preview: str      # excerpt only, never the full body

    EVENT_NAME = 'messaging.new_message_email_requested'
