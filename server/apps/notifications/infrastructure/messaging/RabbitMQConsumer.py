import json
import logging
import os

import pika
from django.conf import settings
from pika.exceptions import ChannelClosedByBroker

from apps.notifications.application.service.NotificationService import NotificationService
from apps.notifications.infrastructure.email.DjangoEmailSender import DjangoEmailSender

logger = logging.getLogger(__name__)


class RabbitMQConsumer:

    EXCHANGE = 'domain_events'
    QUEUE = 'notifications.events'
    # Shared DLX (direct): each queue publishes to it with its own routing key,
    # which lets other modules reuse the same exchange.
    DEAD_LETTER_EXCHANGE = 'domain_events.dlx'
    DEAD_LETTER_QUEUE = 'notifications.events.dlq'
    ROUTING_KEYS = {
        "users.email_verification_requested": "handle_verification_email",
        "users.welcome_email_requested": "handle_welcome_email",
        "users.password_reset_requested": "handle_password_reset_email",
        "messaging.new_message_email_requested": "handle_new_message_email",
    }

    def __init__(self, host: str | None = None):
        self._host = host or os.environ.get('RABBITMQ_HOST', 'rabbitmq')
        self._service = NotificationService(DjangoEmailSender())

    def start(self) -> None:
        credentials = pika.PlainCredentials(
            username=os.environ.get('RABBITMQ_DEFAULT_USER', 'guest'),
            password=os.environ.get('RABBITMQ_DEFAULT_PASS', 'guest'),
        )
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self._host, credentials=credentials)
        )
        channel = connection.channel()

        channel.exchange_declare(
            exchange=self.EXCHANGE,
            exchange_type='direct',
            durable=True,
        )

        channel.exchange_declare(
            exchange=self.DEAD_LETTER_EXCHANGE,
            exchange_type='direct',
            durable=True,
        )
        channel.queue_declare(queue=self.DEAD_LETTER_QUEUE, durable=True)
        channel.queue_bind(
            queue=self.DEAD_LETTER_QUEUE,
            exchange=self.DEAD_LETTER_EXCHANGE,
            routing_key=self.QUEUE,
        )

        try:
            channel.queue_declare(
                queue=self.QUEUE,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': self.DEAD_LETTER_EXCHANGE,
                    'x-dead-letter-routing-key': self.QUEUE,
                },
            )
        except ChannelClosedByBroker as e:
            if e.reply_code == 406:
                raise RuntimeError(
                    f"La file '{self.QUEUE}' existe déjà sans dead-letter exchange. "
                    f"Migration unique (vérifier qu'elle est vide) : "
                    f"docker compose exec rabbitmq rabbitmqctl delete_queue {self.QUEUE}"
                ) from e
            raise

        for routing_key in self.ROUTING_KEYS:
            channel.queue_bind(
                queue=self.QUEUE,
                exchange=self.EXCHANGE,
                routing_key=routing_key,
            )

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=self.QUEUE, on_message_callback=self._handle)

        logger.info("Consumer démarré. En attente de messages...")
        channel.start_consuming()

    def _handle(self, ch, method, properties, body) -> None:
        routing_key = method.routing_key
        try:
            data = json.loads(body)
            handler_name = self.ROUTING_KEYS.get(routing_key)
            if handler_name is None:
                raise ValueError(f"Routing key non gérée : {routing_key}")
            getattr(self, handler_name)(data)
        except Exception:
            # The message goes to the dead letter queue (notifications.events.dlq) instead of being lost
            logger.exception("Échec du traitement de '%s', message envoyé en dead-letter", routing_key)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def handle_verification_email(self, data: dict) -> None:
        self._service.send_verification_email(
            to=data["email"],
            first_name=data["first_name"],
            code=data["code"],
        )
        logger.info("Email de vérification envoyé (user_id=%s)", data.get("user_id"))

    def handle_welcome_email(self, data: dict) -> None:
        self._service.send_welcome_email(
            to=data["email"],
            first_name=data["first_name"],
        )
        logger.info("Email de bienvenue envoyé (user_id=%s)", data.get("user_id"))

    def handle_new_message_email(self, data: dict) -> None:
        # The event is self-contained: no read of the messaging data
        conversation_url = f"{settings.FRONTEND_URL.rstrip('/')}/messages/{data['conversation_id']}"
        self._service.send_new_message_email(
            to=data["recipient_email"],
            first_name=data["recipient_first_name"],
            sender_first_name=data["sender_first_name"],
            hebergement_name=data["hebergement_name"],
            message_preview=data["message_preview"],
            conversation_url=conversation_url,
        )
        logger.info(
            "Email de nouveau message envoyé (outbox_id=%s, conversation=%s)",
            data.get("outbox_id"), data["conversation_id"],
        )

    def handle_password_reset_email(self, data: dict) -> None:
        self._service.send_password_reset_email(
            to=data["email"],
            first_name=data["first_name"],
            code=data["code"],
        )
        logger.info("Email de réinitialisation envoyé (user_id=%s)", data.get("user_id"))
