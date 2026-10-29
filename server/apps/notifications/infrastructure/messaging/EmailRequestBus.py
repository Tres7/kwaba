import json
import logging
import os

import pika

from apps.notifications.infrastructure.messaging.RabbitMQConsumer import RabbitMQConsumer

logger = logging.getLogger(__name__)


class EmailRequestBus:
    EXCHANGE = RabbitMQConsumer.EXCHANGE

    def request(self, routing_key: str, data: dict) -> None:
        if routing_key not in RabbitMQConsumer.ROUTING_KEYS:
            raise ValueError(f"Routing key non gérée : {routing_key}")
        try:
            self._publish(routing_key, data)
            return
        except Exception as e:
            logger.warning("RabbitMQ indisponible (%s) : traitement direct de %s", e, routing_key)
        try:
            RabbitMQConsumer(host='unused').dispatch(routing_key, data)
        except Exception as e:
            logger.warning("Email %s non envoyé : %s", routing_key, type(e).__name__)

    def _publish(self, routing_key: str, data: dict) -> None:
        credentials = pika.PlainCredentials(
            username=os.environ.get('RABBITMQ_DEFAULT_USER', 'guest'),
            password=os.environ.get('RABBITMQ_DEFAULT_PASS', 'guest'),
        )
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=os.environ.get('RABBITMQ_HOST', 'rabbitmq'), credentials=credentials,
            connection_attempts=1, socket_timeout=3, blocked_connection_timeout=3,
        ))
        try:
            channel = connection.channel()
            channel.exchange_declare(exchange=self.EXCHANGE, exchange_type='direct', durable=True)
            channel.basic_publish(
                exchange=self.EXCHANGE, routing_key=routing_key, body=json.dumps(data),
                properties=pika.BasicProperties(delivery_mode=2),
            )
        finally:
            connection.close()
