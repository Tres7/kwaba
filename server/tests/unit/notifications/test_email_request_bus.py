import pytest

from apps.notifications.infrastructure.messaging.EmailRequestBus import EmailRequestBus

ROUTING_KEY = 'hebergements.booking_cancelled_listing_removed'
DATA = {'reservation_id': 'r-1', 'email': 'ama@example.tg', 'first_name': 'Ama', 'hebergement_name': 'Villa Océane',
        'city': 'Lomé', 'check_in': '2026-12-20', 'check_out': '2026-12-23'}


def test_published_on_the_broker_when_it_is_up(monkeypatch, mailoutbox):
    publies = []
    monkeypatch.setattr(EmailRequestBus, '_publish', lambda self, cle, donnees: publies.append((cle, donnees)))

    EmailRequestBus().request(ROUTING_KEY, DATA)

    assert publies == [(ROUTING_KEY, DATA)]
    assert mailoutbox == []


def test_sent_directly_when_the_broker_is_down(monkeypatch, mailoutbox):
    def refuse(self, *args):
        raise ConnectionError('RabbitMQ indisponible')
    monkeypatch.setattr(EmailRequestBus, '_publish', refuse)

    EmailRequestBus().request(ROUTING_KEY, DATA)

    assert [m.to for m in mailoutbox] == [['ama@example.tg']]
    assert 'du 20 décembre au 23 décembre 2026' in mailoutbox[0].body


def test_unknown_event_is_refused_before_publishing(monkeypatch):
    monkeypatch.setattr(EmailRequestBus, '_publish', lambda *args: pytest.fail('published'))

    with pytest.raises(ValueError):
        EmailRequestBus().request('hebergements.unknown', DATA)
