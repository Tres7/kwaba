import threading
from datetime import timedelta

import pytest
from django.db import connection, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.messaging.application.service.OutboxRelayService import OutboxRelayService
from apps.messaging.infrastructure.persistence.DjangoConversationRepository import DjangoConversationRepository
from apps.messaging.infrastructure.persistence.DjangoNotificationOutbox import DjangoNotificationOutbox
from apps.messaging.infrastructure.persistence.DjangoTransactionManager import DjangoTransactionManager
from apps.messaging.infrastructure.persistence.models import (
    ConversationModel,
    MessageModel,
    NotificationOutboxModel,
)
from tests.unit.messaging.fakes import FakeEventPublisher

CONVERSATIONS = '/api/v1/messaging/conversations/'


@pytest.fixture
def conversation(make_user, make_hebergement):
    listing = make_hebergement()
    now = timezone.now()
    return ConversationModel.objects.create(hebergement_id=listing.id, guest_id=make_user().id, host_id=listing.host.id,
                                            created_at=now, last_message_at=now)


@pytest.fixture
def schedule(conversation):
    def _schedule(message_id=1, available_in=-1, status='pending'):
        return NotificationOutboxModel.objects.create(
            event_type='messaging.new_message_email_requested', conversation_id=conversation.id,
            message_id=message_id, recipient_id=conversation.host_id, payload={
                'conversation_id': str(conversation.id),
                'recipient_email': 'hote@example.tg',
                'recipient_first_name': 'Kofi',
                'sender_first_name': 'Ama',
                'hebergement_name': 'Villa test',
                'message_preview': 'Bonjour',
            },
            available_at=timezone.now() + timedelta(seconds=available_in), status=status,
        )

    return _schedule


def _run_in_threads(target, count):
    def wrapped(*args):
        try:
            target(*args)
        finally:
            connection.close()

    threads = [threading.Thread(target=wrapped, args=(i,)) for i in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)


class TestDjangoNotificationOutbox:
    def test_claims_due_pending_rows_in_order(self, schedule):
        later = schedule(message_id=2, available_in=-5)
        earliest = schedule(message_id=1, available_in=-10)
        schedule(message_id=3, available_in=60)
        schedule(message_id=4, available_in=-20, status='sent')

        assert DjangoNotificationOutbox().claim_next_due(timezone.now()).id == earliest.id
        NotificationOutboxModel.objects.filter(pk=earliest.pk).update(status='sent')
        assert DjangoNotificationOutbox().claim_next_due(timezone.now()).id == later.id

    def test_record_failure_increments_attempts(self, schedule):
        row = schedule()
        outbox = DjangoNotificationOutbox()
        retry_at = timezone.now() + timedelta(seconds=10)
        assert outbox.record_failure(row.id, retry_at, 'boom') == 1
        assert outbox.record_failure(row.id, retry_at, 'boom') == 2

    def test_purge_only_old_processed_rows(self, schedule):
        old_sent, old_skipped, recent, pending = schedule(), schedule(), schedule(), schedule()
        long_ago = timezone.now() - timedelta(days=8)
        NotificationOutboxModel.objects.filter(pk__in=[old_sent.pk, old_skipped.pk]).update(processed_at=long_ago)
        NotificationOutboxModel.objects.filter(pk=old_sent.pk).update(status='sent')
        NotificationOutboxModel.objects.filter(pk=old_skipped.pk).update(status='skipped')
        NotificationOutboxModel.objects.filter(pk=recent.pk).update(status='sent', processed_at=timezone.now())

        assert DjangoNotificationOutbox().purge_processed_before(timezone.now() - timedelta(days=7)) == 2
        assert set(NotificationOutboxModel.objects.values_list('pk', flat=True)) == {recent.pk, pending.pk}


class TestRelayWithDatabase:
    def relay(self, publisher):
        return OutboxRelayService(DjangoNotificationOutbox(), DjangoConversationRepository(), publisher,
                                  DjangoTransactionManager())

    def test_due_row_is_published_and_marked_sent(self, schedule):
        publisher = FakeEventPublisher()
        row = schedule(message_id=5)

        assert self.relay(publisher).process_due() == {'sent': 1}
        row.refresh_from_db()
        assert row.status == 'sent'
        assert publisher.published[0][1] == str(row.id)

    def test_row_skipped_when_recipient_already_read(self, conversation, schedule):
        publisher = FakeEventPublisher()
        row = schedule(message_id=5)
        ConversationModel.objects.filter(pk=conversation.pk).update(host_last_read_id=9)

        assert self.relay(publisher).process_due() == {'skipped': 1}
        row.refresh_from_db()
        assert row.status == 'skipped'
        assert publisher.published == []

    def test_failure_is_recorded(self, schedule):
        publisher = FakeEventPublisher()
        publisher.error = ConnectionError('broker down')
        row = schedule()

        assert self.relay(publisher).process_due() == {'failed': 1}
        row.refresh_from_db()
        assert (row.status, row.attempts) == ('pending', 1)
        assert row.available_at > timezone.now()


@pytest.mark.django_db(transaction=True)
def test_two_relays_never_claim_the_same_row(schedule):
    rows = [schedule(message_id=i) for i in range(2)]
    claimed = []
    both_claimed = threading.Barrier(2, timeout=10)

    def claim(_):
        with transaction.atomic():
            entry = DjangoNotificationOutbox().claim_next_due(timezone.now())
            claimed.append(entry.id if entry else None)
            both_claimed.wait()  # keeps the lock as long as the other relay has not claimed its row

    _run_in_threads(claim, 2)
    assert sorted(claimed) == sorted(r.id for r in rows)


@pytest.mark.django_db(transaction=True)
def test_concurrent_sends_are_serialized_and_schedule_one_email(make_user, make_hebergement):
    listing, guest = make_hebergement(), make_user()
    client = APIClient()
    client.force_authenticate(user=guest)
    thread_id = client.post(CONVERSATIONS, {'hebergement_id': str(listing.id)}, format='json').data['id']
    statuses = []

    def send(i):
        sender = APIClient()
        sender.force_authenticate(user=guest)
        statuses.append(sender.post(f'{CONVERSATIONS}{thread_id}/messages/', {'content': f'm{i}'},
                                    format='json').status_code)

    _run_in_threads(send, 20)

    assert statuses == [201] * 20
    last_id = MessageModel.objects.filter(conversation_id=thread_id).order_by('-id').values_list('id', flat=True)[0]
    assert MessageModel.objects.filter(conversation_id=thread_id).count() == 20
    # The sender's cursor never went back despite the parallel sendings
    assert ConversationModel.objects.get(pk=thread_id).guest_last_read_id == last_id
    # 0→1 decision taken only once under the thread lock
    assert NotificationOutboxModel.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_thread_creation_yields_one_thread(make_user, make_hebergement):
    listing, guest = make_hebergement(), make_user()
    statuses = []

    def start(_):
        client = APIClient()
        client.force_authenticate(user=guest)
        statuses.append(client.post(CONVERSATIONS, {'hebergement_id': str(listing.id)}, format='json').status_code)

    _run_in_threads(start, 5)

    assert sorted(statuses) == [200, 200, 200, 200, 201]
    assert ConversationModel.objects.count() == 1
