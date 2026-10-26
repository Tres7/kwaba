from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.messaging.infrastructure.persistence.models import ConversationModel, NotificationOutboxModel

CONVERSATIONS = '/api/v1/messaging/conversations/'
UNREAD = '/api/v1/messaging/unread-count/'


@pytest.fixture
def listing(make_hebergement):
    return make_hebergement()


@pytest.fixture
def guest(make_user):
    return make_user()


@pytest.fixture
def thread(client_for, guest, listing):
    """Thread opened by the traveller; returns its id."""
    response = client_for(guest).post(CONVERSATIONS, {'hebergement_id': str(listing.id)}, format='json')
    assert response.status_code == 201
    return response.data['id']


def _messages_url(thread_id):
    return f'{CONVERSATIONS}{thread_id}/messages/'


class TestStartConversation:
    def test_idempotent(self, client_for, guest, listing, thread):
        response = client_for(guest).post(CONVERSATIONS, {'hebergement_id': str(listing.id)}, format='json')
        assert response.status_code == 200
        assert response.data['id'] == thread
        assert ConversationModel.objects.count() == 1

    def test_unverified_user_forbidden(self, client_for, make_user, listing):
        response = client_for(make_user(is_verified=False)).post(
            CONVERSATIONS, {'hebergement_id': str(listing.id)}, format='json')
        assert response.status_code == 403

    def test_own_listing_forbidden(self, client_for, listing):
        response = client_for(listing.host).post(CONVERSATIONS, {'hebergement_id': str(listing.id)}, format='json')
        assert response.status_code == 403

    @pytest.mark.parametrize('payload', [{}, {'hebergement_id': 'abc'}])
    def test_invalid_listing_id(self, client_for, guest, payload):
        assert client_for(guest).post(CONVERSATIONS, payload, format='json').status_code == 400

    def test_unknown_listing(self, client_for, guest):
        response = client_for(guest).post(
            CONVERSATIONS, {'hebergement_id': '00000000-0000-0000-0000-000000000000'}, format='json')
        assert response.status_code == 404

    def test_eleventh_creation_in_an_hour_is_throttled(self, client_for, guest, make_hebergement):
        client = client_for(guest)
        statuses = [
            client.post(CONVERSATIONS, {'hebergement_id': str(make_hebergement().id)}, format='json').status_code
            for _ in range(11)
        ]
        assert statuses == [201] * 10 + [429]
        # Reads (polling) are not limited
        assert client.get(CONVERSATIONS).status_code == 200


class TestHostOpensThread:
    URL = f'{CONVERSATIONS}avec-voyageur/'

    def test_host_opens_thread_from_reservation(self, client_for, listing, make_reservation):
        reservation = make_reservation(listing)
        client = client_for(listing.host)
        assert client.post(self.URL, {'reservation_id': str(reservation.id)}, format='json').status_code == 201
        assert client.post(self.URL, {'reservation_id': str(reservation.id)}, format='json').status_code == 200

    def test_reservation_of_another_host_or_cancelled(self, client_for, make_user, listing, make_reservation):
        other = make_reservation(listing)
        cancelled = make_reservation(listing, starts_in=30, status='cancelled')
        assert client_for(make_user(role='hote')).post(
            self.URL, {'reservation_id': str(other.id)}, format='json').status_code == 404
        assert client_for(listing.host).post(
            self.URL, {'reservation_id': str(cancelled.id)}, format='json').status_code == 404


class TestMessages:
    def test_send_and_read_back_with_after_cursor(self, client_for, guest, listing, thread):
        sender, receiver = client_for(guest), client_for(listing.host)
        first = sender.post(_messages_url(thread), {'content': 'Bonjour'}, format='json')
        sender.post(_messages_url(thread), {'content': 'Encore moi'}, format='json')

        assert first.status_code == 201
        assert first.data['is_own'] is True
        results = receiver.get(_messages_url(thread)).data['results']
        assert [m['content'] for m in results] == ['Bonjour', 'Encore moi']
        assert [m['is_own'] for m in results] == [False, False]
        after = receiver.get(_messages_url(thread), {'after': first.data['id']}).data['results']
        assert [m['content'] for m in after] == ['Encore moi']

    @pytest.mark.parametrize('content', ['', '   ', 'a' * 2001])
    def test_invalid_content(self, client_for, guest, thread, content):
        assert client_for(guest).post(_messages_url(thread), {'content': content}, format='json').status_code == 400

    @pytest.mark.parametrize('params', [{'after': 'abc'}, {'after': -1}, {'limit': 0}, {'limit': 'abc'}])
    def test_invalid_query_parameters(self, client_for, guest, thread, params):
        assert client_for(guest).get(_messages_url(thread), params).status_code == 400

    def test_non_participant_sees_not_found(self, client_for, make_user, thread):
        stranger = client_for(make_user())
        assert stranger.get(f'{CONVERSATIONS}{thread}/').status_code == 404
        assert stranger.get(_messages_url(thread)).status_code == 404
        assert stranger.post(_messages_url(thread), {'content': 'Intrus'}, format='json').status_code == 404

    def test_thirty_first_message_in_a_minute_is_throttled(self, client_for, guest, thread):
        client = client_for(guest)
        statuses = [
            client.post(_messages_url(thread), {'content': f'm{i}'}, format='json').status_code for i in range(31)
        ]
        assert statuses == [201] * 30 + [429]


class TestUnreadAndNotifications:
    def test_unread_count_and_read_cursor(self, client_for, guest, listing, thread):
        sender, host = client_for(guest), client_for(listing.host)
        for content in ('Un', 'Deux', 'Trois'):
            last = sender.post(_messages_url(thread), {'content': content}, format='json').data['id']

        assert host.get(UNREAD).data['unread_count'] == 3
        assert host.get(CONVERSATIONS).data['results'][0]['unread_count'] == 3
        assert host.post(f'{CONVERSATIONS}{thread}/read/', {'up_to_id': last + 100}, format='json').data == {
            'last_read_id': last,
        }
        assert host.get(UNREAD).data['unread_count'] == 0
        assert host.post(f'{CONVERSATIONS}{thread}/read/', {'up_to_id': 'abc'}, format='json').status_code == 400

    def test_first_unread_rule_in_database(self, client_for, guest, listing, thread, settings):
        sender, host = client_for(guest), client_for(listing.host)

        m1 = sender.post(_messages_url(thread), {'content': 'm1'}, format='json').data
        sender.post(_messages_url(thread), {'content': 'm2'}, format='json')
        [row] = NotificationOutboxModel.objects.all()
        assert row.recipient_id == listing.host.id
        assert row.available_at == m1['created_at'] + timedelta(seconds=settings.MESSAGING['EMAIL_DELAY_SECONDS'])

        host.post(f'{CONVERSATIONS}{thread}/read/', {}, format='json')
        sender.post(_messages_url(thread), {'content': 'm3'}, format='json')
        assert NotificationOutboxModel.objects.count() == 2

    def test_threads_sorted_by_last_message(self, client_for, guest, make_hebergement):
        client = client_for(guest)
        older = client.post(CONVERSATIONS, {'hebergement_id': str(make_hebergement().id)}, format='json').data['id']
        newer = client.post(CONVERSATIONS, {'hebergement_id': str(make_hebergement().id)}, format='json').data['id']
        client.post(_messages_url(older), {'content': 'relance'}, format='json')

        assert [c['id'] for c in client.get(CONVERSATIONS).data['results']] == [older, newer]

    def test_list_query_count_is_constant(self, client_for, guest, make_hebergement):
        client = client_for(guest)

        def create_threads(count):
            for _ in range(count):
                thread_id = client.post(CONVERSATIONS, {'hebergement_id': str(make_hebergement().id)},
                                        format='json').data['id']
                client.post(_messages_url(thread_id), {'content': 'Bonjour'}, format='json')

        create_threads(1)
        with CaptureQueriesContext(connection) as one:
            client.get(CONVERSATIONS)
        create_threads(4)
        with CaptureQueriesContext(connection) as five:
            client.get(CONVERSATIONS)
        assert len(five) == len(one)
