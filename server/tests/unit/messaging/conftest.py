import pytest

from apps.messaging.application.service.MessagingService import MessagingService

from tests.unit.messaging.fakes import (
    EMAIL_DELAY_SECONDS,
    FakeConversationRepository,
    FakeHebergementLookup,
    FakeMessageRepository,
    FakeNotificationOutbox,
    FakeTransactionManager,
    FakeUserLookup,
)


class World:
    """In-memory ports, a host, a traveller and a listing of the host."""

    def __init__(self):
        self.conversations = FakeConversationRepository()
        self.messages = FakeMessageRepository()
        self.hebergements = FakeHebergementLookup()
        self.users = FakeUserLookup()
        self.outbox = FakeNotificationOutbox()
        self.tx = FakeTransactionManager()
        self.host = self.users.add('Kofi')
        self.guest = self.users.add('Ama')
        self.hebergement = self.hebergements.add(self.host.id)

    def service(self):
        return MessagingService(self.conversations, self.messages, self.hebergements, self.users,
                                self.outbox, self.tx, email_delay_seconds=EMAIL_DELAY_SECONDS)


@pytest.fixture
def world():
    return World()


@pytest.fixture
def service(world):
    return world.service()
