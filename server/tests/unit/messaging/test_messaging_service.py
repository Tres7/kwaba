import datetime
import uuid

import pytest

from apps.messaging.application.events.NewMessageEmailRequested import NewMessageEmailRequested
from apps.messaging.domain.entities.Conversation import Conversation
from apps.messaging.domain.entities.Message import Message
from apps.messaging.domain.exceptions import (
    CannotContactOwnHebergementException,
    ConversationNotFoundException,
    HebergementNotFoundException,
    InvalidMessageException,
    NotParticipantException,
)

from tests.unit.messaging.fakes import EMAIL_DELAY_SECONDS


@pytest.fixture
def conversation_id(world, service):
    summary, _ = service.start_conversation(world.guest.id, world.hebergement.id)
    return summary.id


class TestStartConversation:
    def test_is_idempotent(self, world, service):
        first, created = service.start_conversation(world.guest.id, world.hebergement.id)
        second, created_again = service.start_conversation(world.guest.id, world.hebergement.id)
        assert created is True
        assert created_again is False
        assert first.id == second.id
        assert first.my_role == 'guest'
        assert first.other_participant.id == world.host.id

    def test_unknown_hebergement(self, world, service):
        with pytest.raises(HebergementNotFoundException):
            service.start_conversation(world.guest.id, uuid.uuid4())

    def test_host_cannot_contact_own_hebergement(self, world, service):
        with pytest.raises(CannotContactOwnHebergementException):
            service.start_conversation(world.host.id, world.hebergement.id)

    def test_concurrent_creation_returns_winner_thread(self, world, service):
        winner = Conversation.start(world.hebergement.id, world.guest.id, world.host.id)
        world.conversations.next_create_conflicts = True
        world.conversations.concurrent_winner = winner

        summary, created = service.start_conversation(world.guest.id, world.hebergement.id)

        assert created is False
        assert summary.id == winner.id

    def test_integrity_error_without_winner_means_hebergement_gone(self, world, service):
        world.conversations.next_create_conflicts = True
        with pytest.raises(HebergementNotFoundException):
            service.start_conversation(world.guest.id, world.hebergement.id)


class TestOpenAsHost:
    def test_other_host_rejected(self, world, service):
        other_host = world.users.add('Yao')
        with pytest.raises(NotParticipantException):
            service.open_as_host(other_host.id, world.hebergement.id, world.guest.id)

    def test_host_opens_thread_with_guest(self, world, service):
        summary, created = service.open_as_host(world.host.id, world.hebergement.id, world.guest.id)
        assert created is True
        assert summary.my_role == 'host'
        assert summary.other_participant.id == world.guest.id


class TestSendMessage:
    def test_first_message_schedules_email_after_delay(self, world, service, conversation_id):
        message = service.send_message(world.guest.id, conversation_id, 'Bonjour, la villa est-elle libre ?')

        assert message.is_own is True
        [row] = world.outbox.rows
        assert row.entry.event_type == NewMessageEmailRequested.EVENT_NAME
        assert row.entry.recipient_id == world.host.id
        assert row.entry.message_id == message.id
        assert row.available_at == message.created_at + datetime.timedelta(seconds=EMAIL_DELAY_SECONDS)
        assert row.entry.payload['recipient_email'] == world.host.email
        assert row.entry.payload['sender_first_name'] == 'Ama'

    def test_second_unread_message_schedules_nothing(self, world, service, conversation_id):
        service.send_message(world.guest.id, conversation_id, 'Premier')
        service.send_message(world.guest.id, conversation_id, 'Second')
        assert len(world.outbox.rows) == 1

    def test_new_email_once_recipient_has_read(self, world, service, conversation_id):
        service.send_message(world.guest.id, conversation_id, 'Premier')
        service.mark_as_read(world.host.id, conversation_id)
        service.send_message(world.guest.id, conversation_id, 'Après lecture')
        assert len(world.outbox.rows) == 2

    def test_reply_does_not_count_as_read_for_the_other_side(self, world, service, conversation_id):
        service.send_message(world.guest.id, conversation_id, 'Question')
        service.send_message(world.host.id, conversation_id, 'Réponse')
        # The host read while replying; the traveller receives their first notification
        assert [r.entry.recipient_id for r in world.outbox.rows] == [world.host.id, world.guest.id]

    def test_non_participant_gets_not_found(self, world, service, conversation_id):
        stranger = world.users.add('Yao')
        with pytest.raises(ConversationNotFoundException):
            service.send_message(stranger.id, conversation_id, 'Intrus')

    def test_recipient_without_email_no_outbox_no_error(self, world, service, conversation_id):
        world.users.rows[world.host.id].email = ''
        service.send_message(world.guest.id, conversation_id, 'Bonjour')
        assert world.outbox.rows == []

    def test_payload_contains_preview_only(self, world, service, conversation_id):
        service.send_message(world.guest.id, conversation_id, 'mot ' * 200)
        assert len(world.outbox.rows[0].entry.payload['message_preview']) <= 120

    def test_invalid_content_rejected_before_anything_is_written(self, world, service, conversation_id):
        with pytest.raises(InvalidMessageException):
            service.send_message(world.guest.id, conversation_id, '   ')
        assert world.messages.rows == []


class TestReading:
    def test_get_messages_page_size_and_after(self, world, service, conversation_id):
        for i in range(120):
            world.messages.add(Message.compose(conversation_id, world.guest.id, f'm{i}'))

        assert len(service.get_messages(world.host.id, conversation_id)) == 50
        assert len(service.get_messages(world.host.id, conversation_id, limit=500)) == 100
        after = service.get_messages(world.host.id, conversation_id, after_id=115)
        assert [m.id for m in after] == [116, 117, 118, 119, 120]

    def test_get_messages_non_participant(self, world, service, conversation_id):
        with pytest.raises(ConversationNotFoundException):
            service.get_messages(uuid.uuid4(), conversation_id)

    def test_mark_as_read_caps_cursor_at_latest_message(self, world, service, conversation_id):
        service.send_message(world.guest.id, conversation_id, 'Un')
        service.send_message(world.guest.id, conversation_id, 'Deux')
        assert service.mark_as_read(world.host.id, conversation_id, up_to_id=999) == 2

    def test_mark_as_read_never_moves_back(self, world, service, conversation_id):
        service.send_message(world.guest.id, conversation_id, 'Un')
        service.send_message(world.guest.id, conversation_id, 'Deux')
        service.mark_as_read(world.host.id, conversation_id)
        assert service.mark_as_read(world.host.id, conversation_id, up_to_id=1) == 2

    def test_mark_as_read_on_empty_thread_keeps_cursor(self, world, service, conversation_id):
        assert service.mark_as_read(world.host.id, conversation_id) == 0

    def test_unread_total_sums_threads(self, world, service, conversation_id):
        other_guest = world.users.add('Yao')
        other_summary, _ = service.start_conversation(other_guest.id, world.hebergement.id)
        service.send_message(world.guest.id, conversation_id, 'Un')
        service.send_message(world.guest.id, conversation_id, 'Deux')
        service.send_message(other_guest.id, other_summary.id, 'Trois')

        assert service.unread_total(world.host.id) == 3
        assert service.unread_total(world.guest.id) == 0

    def test_list_conversations_with_unread_count(self, world, service, conversation_id):
        service.send_message(world.guest.id, conversation_id, 'Bonjour')
        [summary] = service.list_conversations(world.host.id)
        assert summary.unread_count == 1
        assert summary.last_message.content == 'Bonjour'
        assert summary.hebergement.name == world.hebergement.name

