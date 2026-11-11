import datetime

import pytest

from apps.messaging.application.ports.ModerationGuard import (
    BLOCK, ENFORCE, OBSERVE, OFF, REFUSAL, SIMULATED, WARN, WARNING_IGNORED, ModerationVerdict,
)
from apps.messaging.application.service.MessagingService import MessagingService
from apps.messaging.domain.exceptions import (
    ConfirmationRequiredException, ConversationNotFoundException, MessageRefusedException, MessagingSuspendedException,
)
from tests.unit.messaging.fakes import EMAIL_DELAY_SECONDS, FakeModerationGuard, FakeSanctionRepository

INSULT = ModerationVerdict(BLOCK, ('insult',))
THREAT_WARNING = ModerationVerdict(WARN, ('threat',))


@pytest.fixture
def sanctions():
    return FakeSanctionRepository()


def make_service(world, guard, sanctions):
    return MessagingService(world.conversations, world.messages, world.hebergements, world.users, world.outbox,
                            world.tx, email_delay_seconds=EMAIL_DELAY_SECONDS, moderation=guard, sanctions=sanctions)


@pytest.fixture
def thread(world, service):
    conversation, _ = service.start_conversation(world.guest.id, world.hebergement.id)
    return conversation.id


def test_enforce_refuses_blocked_message_and_records_it(world, sanctions, thread):
    guard = FakeModerationGuard(ENFORCE, INSULT)
    with pytest.raises(MessageRefusedException) as refused:
        make_service(world, guard, sanctions).send_message(world.guest.id, thread, "tu es un idiot")
    assert refused.value.categories == ('insult',)
    assert world.messages.rows == [] and world.outbox.rows == []
    assert [r[2] for r in guard.records] == [REFUSAL]


def test_enforce_warning_requires_confirmation(world, sanctions, thread):
    guard = FakeModerationGuard(ENFORCE, THREAT_WARNING)
    service = make_service(world, guard, sanctions)
    with pytest.raises(ConfirmationRequiredException):
        service.send_message(world.guest.id, thread, "tu vas le regretter")
    assert world.messages.rows == [] and guard.records == []
    sent = service.send_message(world.guest.id, thread, "tu vas le regretter", confirmed=True)
    assert sent.content == "tu vas le regretter"
    assert [r[2] for r in guard.records] == [WARNING_IGNORED]


@pytest.mark.parametrize('verdict', [INSULT, THREAT_WARNING])
def test_observe_delivers_and_records_a_simulated_refusal(world, sanctions, thread, verdict):
    guard = FakeModerationGuard(OBSERVE, verdict)
    sent = make_service(world, guard, sanctions).send_message(world.guest.id, thread, "texte")
    assert sent.id is not None
    assert [(r[2], r[3]) for r in guard.records] == [(SIMULATED, verdict.level)]


def test_off_mode_does_not_screen(world, sanctions, thread):
    guard = FakeModerationGuard(OFF, INSULT)
    make_service(world, guard, sanctions).send_message(world.guest.id, thread, "tu es un idiot")
    assert guard.records == [] and len(world.messages.rows) == 1


def test_suspended_user_can_read_but_not_write(world, sanctions, service, thread):
    sanctions.suspended_until[world.guest.id] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)
    moderated = make_service(world, FakeModerationGuard(), sanctions)
    with pytest.raises(MessagingSuspendedException):
        moderated.send_message(world.guest.id, thread, "Bonjour")
    assert moderated.get_messages(world.guest.id, thread) == []
    assert moderated.start_conversation(world.guest.id, world.hebergement.id)[1] is False


def test_suspended_user_cannot_open_a_new_thread(world, sanctions):
    other = world.hebergements.add(world.host.id, name='Villa Kpalimé')
    sanctions.suspended_until[world.guest.id] = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)
    with pytest.raises(MessagingSuspendedException):
        make_service(world, FakeModerationGuard(), sanctions).start_conversation(world.guest.id, other.id)


def test_refusal_is_not_recorded_for_a_stranger_thread(world, sanctions, thread):
    stranger = world.users.add('Yao')
    guard = FakeModerationGuard(ENFORCE, INSULT)
    with pytest.raises(ConversationNotFoundException):
        make_service(world, guard, sanctions).send_message(stranger.id, thread, "tu es un idiot")
    assert guard.records == []
