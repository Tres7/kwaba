import datetime
from typing import Optional
import uuid

from django.db.models import F

from apps.messaging.application.ports.NotificationOutbox import NotificationOutbox, OutboxEntry
from apps.messaging.infrastructure.persistence.models import NotificationOutboxModel as Outbox


class DjangoNotificationOutbox(NotificationOutbox):

    def schedule(
        self,
        event_type: str,
        conversation_id: uuid.UUID,
        message_id: int,
        recipient_id: uuid.UUID,
        payload: dict,
        available_at: datetime.datetime,
    ) -> None:
        Outbox.objects.create(
            event_type=event_type,
            conversation_id=conversation_id,
            message_id=message_id,
            recipient_id=recipient_id,
            payload=payload,
            available_at=available_at,
        )

    def claim_next_due(self, now: datetime.datetime) -> Optional[OutboxEntry]:
        # SELECT ... FOR UPDATE SKIP LOCKED: a row already taken by another relay is skipped
        model = (
            Outbox.objects.select_for_update(skip_locked=True)
            .filter(status=Outbox.STATUS_PENDING, available_at__lte=now)
            .order_by('available_at', 'id')
            .first()
        )
        if model is None:
            return None
        return OutboxEntry(
            id=model.id,
            event_type=model.event_type,
            conversation_id=model.conversation_id,
            message_id=model.message_id,
            recipient_id=model.recipient_id,
            payload=model.payload,
            attempts=model.attempts,
        )

    def mark_sent(self, entry_id: int, now: datetime.datetime) -> None:
        Outbox.objects.filter(id=entry_id).update(status=Outbox.STATUS_SENT, processed_at=now)

    def mark_skipped(self, entry_id: int, now: datetime.datetime, reason: str) -> None:
        Outbox.objects.filter(id=entry_id).update(
            status=Outbox.STATUS_SKIPPED, processed_at=now, skip_reason=reason[:200],
        )

    def postpone(self, entry_id: int, available_at: datetime.datetime) -> None:
        Outbox.objects.filter(id=entry_id).update(available_at=available_at)

    def record_failure(self, entry_id: int, available_at: datetime.datetime, error: str) -> int:
        Outbox.objects.filter(id=entry_id).update(
            attempts=F('attempts') + 1, last_error=error, available_at=available_at,
        )
        return Outbox.objects.values_list('attempts', flat=True).get(id=entry_id)

    def sent_since(self, recipient_id: uuid.UUID, since: datetime.datetime) -> list:
        return list(
            Outbox.objects.filter(
                recipient_id=recipient_id, status=Outbox.STATUS_SENT, processed_at__gte=since,
            ).order_by('processed_at').values_list('processed_at', flat=True)
        )

    def purge_processed_before(self, before: datetime.datetime) -> int:
        deleted, _ = Outbox.objects.filter(
            status__in=[Outbox.STATUS_SENT, Outbox.STATUS_SKIPPED], processed_at__lt=before,
        ).delete()
        return deleted
