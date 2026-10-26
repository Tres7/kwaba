# Assembly point of the module: wires the application services to their infrastructure adapters.
from django.conf import settings

from apps.messaging.application.service.MessagingService import MessagingService
from apps.messaging.application.service.OutboxRelayService import OutboxRelayService
from apps.messaging.infrastructure.lookups.DjangoBookingLookup import DjangoBookingLookup
from apps.messaging.infrastructure.lookups.DjangoHebergementLookup import DjangoHebergementLookup
from apps.messaging.infrastructure.lookups.DjangoUserLookup import DjangoUserLookup
from apps.messaging.infrastructure.messaging.RabbitMQEventBus import RabbitMQEventBus
from apps.messaging.infrastructure.persistence.DjangoConversationRepository import DjangoConversationRepository
from apps.messaging.infrastructure.persistence.DjangoMessageRepository import DjangoMessageRepository
from apps.messaging.infrastructure.persistence.DjangoNotificationOutbox import DjangoNotificationOutbox
from apps.messaging.infrastructure.persistence.DjangoTransactionManager import DjangoTransactionManager
from apps.messaging.infrastructure.securite.DjangoContactGuard import DjangoContactGuard


def messaging_service() -> MessagingService:
    return MessagingService(
        conversations=DjangoConversationRepository(),
        messages=DjangoMessageRepository(),
        hebergements=DjangoHebergementLookup(),
        users=DjangoUserLookup(),
        outbox=DjangoNotificationOutbox(),
        tx=DjangoTransactionManager(),
        email_delay_seconds=settings.MESSAGING['EMAIL_DELAY_SECONDS'],
        guard=DjangoContactGuard(),
        bookings=DjangoBookingLookup(),
    )


def outbox_relay_service() -> OutboxRelayService:
    return OutboxRelayService(
        outbox=DjangoNotificationOutbox(),
        conversations=DjangoConversationRepository(),
        publisher=RabbitMQEventBus(),
        tx=DjangoTransactionManager(),
        hourly_cap=settings.MESSAGING['EMAIL_HOURLY_CAP'],
        retention_days=settings.MESSAGING['OUTBOX_RETENTION_DAYS'],
    )
