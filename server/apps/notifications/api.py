from .infrastructure.email.envoi import send_mail
from .infrastructure.messaging.EmailRequestBus import EmailRequestBus
from .infrastructure.messaging.RabbitMQConsumer import RabbitMQConsumer

__all__ = ['demander_email', 'send_mail', 'traiter']


def demander_email(routing_key: str, data: dict) -> None:
    EmailRequestBus().request(routing_key, data)


def traiter(routing_key: str, data: dict) -> None:
    if routing_key in RabbitMQConsumer.ROUTING_KEYS:
        RabbitMQConsumer(host='unused').dispatch(routing_key, data)
