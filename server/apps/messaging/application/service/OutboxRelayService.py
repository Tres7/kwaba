from collections import Counter
import datetime
import logging

from apps.messaging.application.events.NewMessageEmailRequested import NewMessageEmailRequested
from apps.messaging.application.ports.EventPublisher import EventPublisher
from apps.messaging.application.ports.NotificationOutbox import NotificationOutbox, OutboxEntry
from apps.messaging.application.ports.TransactionManager import TransactionManager
from apps.messaging.domain.repositories.ConversationRepository import ConversationRepository

logger = logging.getLogger(__name__)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class OutboxRelayService:
    """Publishes the due notifications of the outbox.

    - One row per transaction, locked with skip locked: two relays never process the same row.
    - At-least-once delivery: if the relay crashes between the publication and the marking,
      the row will be published again. The outbox_id travels in the event to allow deduplication.
    - Never gives up on a publication failure: the row is postponed with a growing (capped) delay.
    """

    WARN_AFTER_ATTEMPTS = 5

    def __init__(
        self,
        outbox: NotificationOutbox,
        conversations: ConversationRepository,
        publisher: EventPublisher,
        tx: TransactionManager,
        hourly_cap: int = 5,
        retention_days: int = 7,
        base_backoff_seconds: int = 10,
        max_backoff_seconds: int = 600,
    ):
        self._outbox = outbox
        self._conversations = conversations
        self._publisher = publisher
        self._tx = tx
        self._hourly_cap = hourly_cap
        self._retention = datetime.timedelta(days=retention_days)
        self._base_backoff = base_backoff_seconds
        self._max_backoff = max_backoff_seconds

    def process_due(self, max_entries: int = 20) -> Counter:
        stats = Counter()
        for _ in range(max_entries):
            with self._tx.atomic():
                now = _now()
                entry = self._outbox.claim_next_due(now)
                if entry is None:
                    break
                result = self._process(entry, now)
            stats[result] += 1
            if result == 'failed':
                # Circuit breaker: if the broker is unavailable, no point trying the next rows
                # (each try may take several seconds and would use an attempt for nothing).
                # They stay due and will be tried at the next pass.
                break
        return stats

    def purge(self) -> int:
        return self._outbox.purge_processed_before(_now() - self._retention)

    def _process(self, entry: OutboxEntry, now: datetime.datetime) -> str:
        conversation = self._conversations.find_by_id(entry.conversation_id)
        if conversation is None:
            self._outbox.mark_skipped(entry.id, now, "conversation introuvable")
            return 'skipped'

        # Check again by ids: has the recipient read this message (or a more recent one) in the meantime?
        if conversation.last_read_id_for(entry.recipient_id) >= entry.message_id:
            self._outbox.mark_skipped(entry.id, now, "déjà lu par le destinataire")
            return 'skipped'

        # Cap per recipient over a sliding hour: postpone, never lose
        sent = self._outbox.sent_since(entry.recipient_id, now - datetime.timedelta(hours=1))
        if len(sent) >= self._hourly_cap:
            # A slot frees up when enough sendings leave the window to get back under the cap
            free_at = sent[len(sent) - self._hourly_cap] + datetime.timedelta(hours=1)
            self._outbox.postpone(entry.id, free_at)
            return 'postponed'

        event = NewMessageEmailRequested(
            event=NewMessageEmailRequested.EVENT_NAME,
            outbox_id=entry.id,
            **entry.payload,
        )
        try:
            self._publisher.publish(event, message_id=str(entry.id))
        except Exception as e:
            attempts = entry.attempts + 1
            delay = min(self._base_backoff * 2 ** (attempts - 1), self._max_backoff)
            attempts = self._outbox.record_failure(
                entry.id, now + datetime.timedelta(seconds=delay), repr(e)[:500],
            )
            log = logger.warning if attempts >= self.WARN_AFTER_ATTEMPTS else logger.info
            log("Publication échouée (outbox_id=%s, tentative %s, prochain essai dans %ss) : %r",
                entry.id, attempts, delay, e)
            return 'failed'

        self._outbox.mark_sent(entry.id, now)
        return 'sent'
