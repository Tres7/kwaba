import logging

from django.conf import settings

from apps.users.application.ports.EventPublisher import EventPublisher
from apps.users.application.events.DomainEvent import DomainEvent
from apps.users.infrastructure.messaging.RabbitMQEventBus import RabbitMQEventBus
from apps.notifications.api import traiter

logger = logging.getLogger(__name__)


class FallbackEventBus(EventPublisher):
    """Publishes on RabbitMQ; if the broker is unavailable, processes the event
    directly so that the emails (verification code, welcome) still go out."""

    def __init__(self, primary: EventPublisher | None = None):
        self._primary = primary or RabbitMQEventBus()

    def publish(self, event: DomainEvent) -> None:
        # In development, the code can still be found in the logs even if the email does not arrive
        code = getattr(event, 'code', None)
        if settings.DEBUG and code:
            logger.warning("[DEV] Code %s pour %s : %s", event.event, getattr(event, 'email', '?'), code)

        try:
            self._primary.publish(event)
            return
        except Exception as e:
            logger.warning("RabbitMQ indisponible (%s) : traitement direct de %s", e, event.event)

        data = event.__dict__
        try:
            traiter(event.event, data)
        except Exception as e:
            # Never the content of the event: it contains the code (in development, it is already in the logs
            # above). No email either, the id is enough to find the account.
            logger.warning("Email %s non envoyé (user_id=%s) : %s", event.event, data.get('user_id'), type(e).__name__)
