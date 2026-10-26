import datetime
import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.messaging.infrastructure.container import outbox_relay_service

logger = logging.getLogger('apps.messaging.relay')

PURGE_EVERY = datetime.timedelta(hours=1)


class Command(BaseCommand):
    help = "Relais de l'outbox de messagerie : publie sur RabbitMQ les notifications échues."

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Traite une seule passe puis s\'arrête.')
        parser.add_argument(
            '--interval', type=int, default=settings.MESSAGING['RELAY_INTERVAL_SECONDS'],
            help='Secondes entre deux passes.',
        )

    def handle(self, *args, **options):
        relay = outbox_relay_service()
        interval = options['interval']
        last_purge = None
        logger.info("Relais démarré (intervalle %ss)", interval)

        while True:
            # Long-running process: close the database connections that became invalid
            close_old_connections()
            try:
                stats = relay.process_due()
                if stats:
                    logger.info("Outbox traitée : %s", dict(stats))

                now = datetime.datetime.now(datetime.timezone.utc)
                if last_purge is None or now - last_purge >= PURGE_EVERY:
                    purged = relay.purge()
                    last_purge = now
                    if purged:
                        logger.info("Rétention : %s ligne(s) d'outbox supprimée(s)", purged)
            except Exception:
                # Database unavailable for example: log it and try again at the next pass
                logger.exception("Erreur pendant la passe du relais")

            if options['once']:
                break
            time.sleep(interval)
