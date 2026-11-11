# Assembly point of the module: wires the application services to their infrastructure adapters.
from django.conf import settings

import datetime

from apps.messaging.application.service.MessagingService import MessagingService
from apps.messaging.application.service.ModerationService import ModerationService, ModerationSettings
from apps.messaging.domain.services.SanctionLadder import LadderPolicy
from apps.messaging.application.service.OutboxRelayService import OutboxRelayService
from apps.messaging.infrastructure.lookups.DjangoBookingLookup import DjangoBookingLookup
from apps.messaging.infrastructure.lookups.DjangoHebergementLookup import DjangoHebergementLookup
from apps.messaging.infrastructure.lookups.DjangoUserLookup import DjangoUserLookup
from apps.messaging.infrastructure.messaging.RabbitMQEventBus import RabbitMQEventBus
from apps.messaging.infrastructure.persistence.DjangoConversationRepository import DjangoConversationRepository
from apps.messaging.infrastructure.persistence.DjangoMessageRepository import DjangoMessageRepository
from apps.messaging.infrastructure.persistence.DjangoNotificationOutbox import DjangoNotificationOutbox
from apps.messaging.infrastructure.email.DjangoSanctionNotifier import DjangoSanctionNotifier
from apps.messaging.infrastructure.persistence.DjangoReportRepository import DjangoReportRepository
from apps.messaging.infrastructure.persistence.DjangoSanctionRepository import DjangoSanctionRepository
from apps.messaging.infrastructure.persistence.DjangoTransactionManager import DjangoTransactionManager
from apps.messaging.infrastructure.securite.DjangoContactGuard import DjangoContactGuard
from apps.messaging.infrastructure.securite.DjangoModerationGuard import DjangoModerationGuard
from apps.messaging.infrastructure.securite.DjangoModerationQueue import DjangoModerationQueue


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
        moderation=DjangoModerationGuard(),
        sanctions=DjangoSanctionRepository(),
    )


def moderation_settings() -> ModerationSettings:
    config = settings.MODERATION
    return ModerationSettings(
        policy=LadderPolicy(
            window=datetime.timedelta(days=config['WINDOW_DAYS']),
            warning_threshold=config['WARNING_THRESHOLD'],
            suspension_threshold=config['SUSPENSION_THRESHOLD'],
            short_suspension=datetime.timedelta(hours=config['FIRST_SUSPENSION_HOURS']),
            long_suspension=datetime.timedelta(days=config['SECOND_SUSPENSION_DAYS']),
        ),
        contest_delay=datetime.timedelta(days=config['CONTEST_DAYS']),
        context_messages=config['CONTEXT_MESSAGES'],
        context_period=datetime.timedelta(days=config['CONTEXT_DAYS']),
        abusive_reporter_threshold=config['ABUSIVE_REPORTER_THRESHOLD'],
    )


def moderation_service() -> ModerationService:
    return ModerationService(
        conversations=DjangoConversationRepository(),
        messages=DjangoMessageRepository(),
        reports=DjangoReportRepository(),
        sanctions=DjangoSanctionRepository(),
        guard=DjangoModerationGuard(),
        queue=DjangoModerationQueue(),
        notifier=DjangoSanctionNotifier(),
        tx=DjangoTransactionManager(),
        settings=moderation_settings(),
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
