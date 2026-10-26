"""In-memory implementations of the messaging ports, faithful to the Django adapters."""
import contextlib
import dataclasses
import datetime
import uuid
from typing import Dict, List, Optional

from apps.messaging.application.ports.EventPublisher import EventPublisher
from apps.messaging.application.ports.HebergementLookup import HebergementInfo, HebergementLookup
from apps.messaging.application.ports.NotificationOutbox import NotificationOutbox, OutboxEntry
from apps.messaging.application.ports.TransactionManager import TransactionManager
from apps.messaging.application.ports.UserLookup import UserInfo, UserLookup
from apps.messaging.domain.entities.Conversation import Conversation
from apps.messaging.domain.entities.Message import Message
from apps.messaging.domain.exceptions import ConversationAlreadyExistsException
from apps.messaging.domain.repositories.ConversationRepository import ConversationRepository
from apps.messaging.domain.repositories.MessageRepository import MessageRepository

EMAIL_DELAY_SECONDS = 60


class FakeConversationRepository(ConversationRepository):
    """Returns copies: an unsaved change is not persisted, as with the ORM."""

    def __init__(self):
        self.rows: Dict[uuid.UUID, Conversation] = {}
        # The next creation violates an integrity constraint...
        self.next_create_conflicts = False
        # ... because the other request has just inserted this thread (None: the listing is gone)
        self.concurrent_winner: Optional[Conversation] = None

    def find_by_id(self, conversation_id):
        row = self.rows.get(conversation_id)
        return dataclasses.replace(row) if row else None

    def find_by_id_for_update(self, conversation_id):
        return self.find_by_id(conversation_id)

    def find_by_hebergement_and_guest(self, hebergement_id, guest_id):
        for row in self.rows.values():
            if row.hebergement_id == hebergement_id and row.guest_id == guest_id:
                return dataclasses.replace(row)
        return None

    def create(self, conversation):
        if self.next_create_conflicts:
            self.next_create_conflicts = False
            if self.concurrent_winner is not None:
                self.rows[self.concurrent_winner.id] = self.concurrent_winner
            raise ConversationAlreadyExistsException()
        if self.find_by_hebergement_and_guest(conversation.hebergement_id, conversation.guest_id):
            raise ConversationAlreadyExistsException()
        self.rows[conversation.id] = dataclasses.replace(conversation)
        return dataclasses.replace(conversation)

    def save(self, conversation):
        self.rows[conversation.id] = dataclasses.replace(conversation)

    def list_for_user(self, user_id):
        rows = [dataclasses.replace(r) for r in self.rows.values() if r.is_participant(user_id)]
        return sorted(rows, key=lambda c: c.last_message_at, reverse=True)


class FakeMessageRepository(MessageRepository):
    def __init__(self):
        self.rows: List[Message] = []

    def add(self, message):
        saved = dataclasses.replace(message, id=len(self.rows) + 1)
        self.rows.append(saved)
        return dataclasses.replace(saved)

    def _of(self, conversation_id):
        return [m for m in self.rows if m.conversation_id == conversation_id]

    def list(self, conversation_id, after_id, limit):
        messages = self._of(conversation_id)
        if after_id is not None:
            return [m for m in messages if m.id > after_id][:limit]
        return messages[-limit:]

    def latest_id(self, conversation_id):
        messages = self._of(conversation_id)
        return messages[-1].id if messages else None

    def has_unread_for(self, conversation, user_id):
        return self._unread(conversation, user_id) > 0

    def last_messages(self, conversation_ids):
        return {cid: self._of(cid)[-1] for cid in conversation_ids if self._of(cid)}

    def unread_counts(self, user_id, conversations):
        counts = {c.id: self._unread(c, user_id) for c in conversations}
        return {cid: n for cid, n in counts.items() if n}

    def _unread(self, conversation, user_id):
        cursor = conversation.last_read_id_for(user_id)
        return sum(1 for m in self._of(conversation.id) if m.id > cursor and m.sender_id != user_id)


class FakeHebergementLookup(HebergementLookup):
    def __init__(self):
        self.rows: Dict[uuid.UUID, HebergementInfo] = {}

    def add(self, host_id, name='Villa Lomé'):
        info = HebergementInfo(id=uuid.uuid4(), name=name, host_id=host_id, city='Lomé', image_url='')
        self.rows[info.id] = info
        return info

    def get(self, hebergement_id):
        return self.rows.get(hebergement_id)

    def get_many(self, hebergement_ids):
        return {i: self.rows[i] for i in hebergement_ids if i in self.rows}


class FakeUserLookup(UserLookup):
    def __init__(self):
        self.rows: Dict[uuid.UUID, UserInfo] = {}

    def add(self, first_name, email=None):
        info = UserInfo(id=uuid.uuid4(), first_name=first_name, last_name='Test',
                        email=f'{first_name.lower()}@example.tg' if email is None else email, avatar_url=None)
        self.rows[info.id] = info
        return info

    def get(self, user_id):
        return self.rows.get(user_id)

    def get_many(self, user_ids):
        return {i: self.rows[i] for i in user_ids if i in self.rows}


@dataclasses.dataclass
class OutboxRow:
    entry: OutboxEntry
    available_at: datetime.datetime
    status: str = 'pending'
    processed_at: Optional[datetime.datetime] = None
    reason: str = ''


class FakeNotificationOutbox(NotificationOutbox):
    def __init__(self):
        self.rows: List[OutboxRow] = []
        self.sent_at: Dict[uuid.UUID, List[datetime.datetime]] = {}

    def schedule(self, event_type, conversation_id, message_id, recipient_id, payload, available_at):
        entry = OutboxEntry(id=len(self.rows) + 1, event_type=event_type, conversation_id=conversation_id,
                            message_id=message_id, recipient_id=recipient_id, payload=payload, attempts=0)
        self.rows.append(OutboxRow(entry=entry, available_at=available_at))

    def claim_next_due(self, now):
        due = [r for r in self.rows if r.status == 'pending' and r.available_at <= now]
        due.sort(key=lambda r: (r.available_at, r.entry.id))
        return dataclasses.replace(due[0].entry) if due else None

    def _row(self, entry_id):
        return next(r for r in self.rows if r.entry.id == entry_id)

    def mark_sent(self, entry_id, now):
        row = self._row(entry_id)
        row.status, row.processed_at = 'sent', now
        self.sent_at.setdefault(row.entry.recipient_id, []).append(now)

    def mark_skipped(self, entry_id, now, reason):
        row = self._row(entry_id)
        row.status, row.processed_at, row.reason = 'skipped', now, reason

    def postpone(self, entry_id, available_at):
        self._row(entry_id).available_at = available_at

    def record_failure(self, entry_id, available_at, error):
        row = self._row(entry_id)
        row.entry.attempts += 1
        row.available_at, row.reason = available_at, error
        return row.entry.attempts

    def sent_since(self, recipient_id, since):
        return sorted(t for t in self.sent_at.get(recipient_id, []) if t >= since)

    def purge_processed_before(self, before):
        kept = [r for r in self.rows if not (r.status in ('sent', 'skipped') and r.processed_at < before)]
        purged = len(self.rows) - len(kept)
        self.rows = kept
        return purged


class FakeTransactionManager(TransactionManager):
    def atomic(self):
        return contextlib.nullcontext()


class FakeEventPublisher(EventPublisher):
    def __init__(self):
        self.published = []
        self.error: Optional[Exception] = None

    def publish(self, event, message_id=None):
        if self.error:
            raise self.error
        self.published.append((event, message_id))
