import json
from types import SimpleNamespace

import pytest

from apps.notifications.infrastructure.messaging.RabbitMQConsumer import RabbitMQConsumer


class FakeChannel:
    def __init__(self):
        self.acked, self.nacked = [], []

    def basic_ack(self, delivery_tag):
        self.acked.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.nacked.append((delivery_tag, requeue))


EVENTS = {
    'users.email_verification_requested': {'user_id': 'u1', 'email': 'ama@example.tg', 'first_name': 'Ama',
                                           'code': '482913'},
    'users.welcome_email_requested': {'user_id': 'u1', 'email': 'ama@example.tg', 'first_name': 'Ama'},
    'users.password_reset_requested': {'user_id': 'u1', 'email': 'ama@example.tg', 'first_name': 'Ama',
                                       'code': '105377'},
    'messaging.new_message_email_requested': {
        'outbox_id': 7, 'conversation_id': 'c-42', 'recipient_email': 'kofi@example.tg',
        'recipient_first_name': 'Kofi', 'sender_first_name': 'Ama', 'hebergement_name': 'Villa Océane',
        'message_preview': 'Bonjour',
    },
    'hebergements.booking_cancelled_listing_removed': {
        'reservation_id': 'r-1', 'email': 'ama@example.tg', 'first_name': 'Ama', 'hebergement_name': 'Villa Océane',
        'city': 'Lomé', 'check_in': '2026-12-20', 'check_out': '2026-12-23',
    },
}


@pytest.fixture
def channel():
    return FakeChannel()


def _deliver(channel, routing_key, body):
    RabbitMQConsumer(host='unused')._handle(channel, SimpleNamespace(routing_key=routing_key, delivery_tag=1),
                                             None, body)


@pytest.mark.parametrize('routing_key', EVENTS)
def test_known_event_sends_email_then_acks(channel, mailoutbox, routing_key):
    _deliver(channel, routing_key, json.dumps(EVENTS[routing_key]))
    assert channel.acked == [1]
    assert channel.nacked == []
    assert len(mailoutbox) == 1


@pytest.mark.parametrize('routing_key, body', [
    ('users.unknown_event', json.dumps({'email': 'ama@example.tg'})),
    ('users.welcome_email_requested', '{pas du json'),
    ('users.welcome_email_requested', json.dumps({'email': 'ama@example.tg'})),
])
def test_unprocessable_message_goes_to_dead_letter(channel, mailoutbox, routing_key, body):
    _deliver(channel, routing_key, body)
    assert channel.acked == []
    assert channel.nacked == [(1, False)]
    assert mailoutbox == []


def test_new_message_link_has_no_double_slash(channel, mailoutbox, settings):
    settings.FRONTEND_URL = 'https://kwaba.example/'
    _deliver(channel, 'messaging.new_message_email_requested',
             json.dumps(EVENTS['messaging.new_message_email_requested']))
    assert 'https://kwaba.example/messages/c-42' in mailoutbox[0].body
