import datetime
import sys

import pytest

from apps.messaging.application.service.OutboxRelayService import OutboxRelayService
from apps.messaging.domain.entities.Conversation import Conversation
from tests.unit.messaging.fakes import FakeEventPublisher

NOW = datetime.datetime(2026, 10, 8, 12, 0, tzinfo=datetime.timezone.utc)
HOUR = datetime.timedelta(hours=1)


@pytest.fixture
def clock(monkeypatch):
    """Relay clock, that the test can move forward."""
    class Clock:
        now = NOW

    module = sys.modules[OutboxRelayService.__module__]
    monkeypatch.setattr(module, '_now', lambda: Clock.now)
    return Clock


@pytest.fixture
def publisher():
    return FakeEventPublisher()


@pytest.fixture
def relay(world, publisher, clock):
    return OutboxRelayService(world.outbox, world.conversations, publisher, world.tx,
                              hourly_cap=5, retention_days=7, base_backoff_seconds=10, max_backoff_seconds=600)


@pytest.fixture
def conversation(world):
    conversation = Conversation.start(world.hebergement.id, world.guest.id, world.host.id)
    world.conversations.save(conversation)
    return conversation


def _schedule(world, conversation, message_id, available_at=NOW):
    world.outbox.schedule(
        event_type='messaging.new_message_email_requested',
        conversation_id=conversation.id,
        message_id=message_id,
        recipient_id=world.host.id,
        payload={
            'conversation_id': str(conversation.id),
            'recipient_email': world.host.email,
            'recipient_first_name': world.host.first_name,
            'sender_first_name': world.guest.first_name,
            'hebergement_name': world.hebergement.name,
            'message_preview': 'Bonjour',
        },
        available_at=available_at,
    )
    return world.outbox.rows[-1]


def test_publishes_due_entry_with_outbox_id_as_message_id(world, relay, publisher, conversation):
    row = _schedule(world, conversation, message_id=1)

    assert relay.process_due() == {'sent': 1}
    [(event, message_id)] = publisher.published
    assert message_id == str(row.entry.id)
    assert event.outbox_id == row.entry.id
    assert row.status == 'sent'


def test_future_entry_not_processed(world, relay, publisher, conversation):
    row = _schedule(world, conversation, message_id=1, available_at=NOW + datetime.timedelta(seconds=1))
    assert relay.process_due() == {}
    assert row.status == 'pending'


def test_skipped_when_recipient_already_read(world, relay, publisher, conversation):
    conversation.mark_read(world.host.id, 3)
    world.conversations.save(conversation)
    row = _schedule(world, conversation, message_id=2)

    assert relay.process_due() == {'skipped': 1}
    assert publisher.published == []
    assert row.status == 'skipped'


def test_skipped_when_conversation_deleted(world, relay, conversation):
    row = _schedule(world, conversation, message_id=1)
    del world.conversations.rows[conversation.id]
    assert relay.process_due() == {'skipped': 1}
    assert row.status == 'skipped'


def test_hourly_cap_postpones_until_a_slot_frees_up(world, relay, conversation, clock):
    first_sent = NOW - datetime.timedelta(minutes=50)
    world.outbox.sent_at[world.host.id] = [first_sent + datetime.timedelta(minutes=i) for i in range(5)]
    row = _schedule(world, conversation, message_id=1)

    assert relay.process_due() == {'postponed': 1}
    assert row.status == 'pending'
    assert row.available_at == first_sent + HOUR


def test_failure_records_attempt_with_exponential_backoff(world, relay, publisher, conversation, clock):
    publisher.error = ConnectionError('broker down')
    row = _schedule(world, conversation, message_id=1)

    delays = []
    for _ in range(8):
        assert relay.process_due() == {'failed': 1}
        delays.append((row.available_at - clock.now).total_seconds())
        clock.now = row.available_at

    assert row.entry.attempts == 8
    assert delays == [10, 20, 40, 80, 160, 320, 600, 600]


def test_first_failure_stops_the_pass(world, relay, publisher, conversation):
    publisher.error = ConnectionError('broker down')
    first, second = _schedule(world, conversation, 1), _schedule(world, conversation, 2)

    assert relay.process_due() == {'failed': 1}
    assert first.entry.attempts == 1
    assert second.entry.attempts == 0


def test_resumes_once_broker_is_back(world, relay, publisher, conversation, clock):
    publisher.error = ConnectionError('broker down')
    row = _schedule(world, conversation, message_id=1)
    relay.process_due()

    publisher.error = None
    clock.now = row.available_at
    assert relay.process_due() == {'sent': 1}


def test_purge_uses_retention(world, relay, conversation, clock):
    old, recent = _schedule(world, conversation, 1), _schedule(world, conversation, 2)
    world.outbox.mark_sent(old.entry.id, NOW - datetime.timedelta(days=8))
    world.outbox.mark_skipped(recent.entry.id, NOW - datetime.timedelta(days=6), 'déjà lu')
    pending = _schedule(world, conversation, 3, available_at=NOW + HOUR)

    assert relay.purge() == 1
    assert [r.entry.id for r in world.outbox.rows] == [recent.entry.id, pending.entry.id]
