import json
import os
from typing import Optional

import pika

from apps.messaging.application.events.DomainEvent import DomainEvent
from apps.messaging.application.ports.EventPublisher import EventPublisher


class RabbitMQEventBus(EventPublisher):
    """Publication used only by the relay (never in an HTTP request).

    - Short timeouts: the relay keeps an outbox row locked during the call.
    - Publisher confirms + mandatory: a publication only counts as successful if the broker
      accepted it AND routed it to at least one queue. Otherwise an exception is raised and the row
      stays to be published again (instead of being marked sent then lost).
    """

    EXCHANGE = 'domain_events'

    def __init__(self, host: str = 'rabbitmq', timeout_seconds: float = 3):
        self._host = host
        self._timeout = timeout_seconds

    def publish(self, event: DomainEvent, message_id: Optional[str] = None) -> None:
        credentials = pika.PlainCredentials(
            username=os.environ.get('RABBITMQ_DEFAULT_USER', 'guest'),
            password=os.environ.get('RABBITMQ_DEFAULT_PASS', 'guest'),
        )
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=self._host,
            credentials=credentials,
            connection_attempts=1,
            socket_timeout=self._timeout,
            stack_timeout=self._timeout + 2,
            blocked_connection_timeout=self._timeout,
        ))
        try:
            channel = connection.channel()
            channel.exchange_declare(exchange=self.EXCHANGE, exchange_type='direct', durable=True)
            channel.confirm_delivery()
            # Raises UnroutableError if no queue is bound to this routing key, NackError if refused
            channel.basic_publish(
                exchange=self.EXCHANGE,
                routing_key=event.event,
                body=json.dumps(event.__dict__),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json',
                    message_id=message_id,
                ),
                mandatory=True,
            )
        finally:
            connection.close()
