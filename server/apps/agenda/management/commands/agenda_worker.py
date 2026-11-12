import logging
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.agenda.infrastructure.container import agenda_service

logger = logging.getLogger('apps.agenda.worker')


class Command(BaseCommand):
    help = "Agenda worker: agents' evening digest, host reminders, availability reminders and alerts."

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Run a single pass, then stop.')
        parser.add_argument('--interval', type=int, default=300, help='Seconds between two passes.')

    def handle(self, *args, **options):
        logger.info("Agenda worker started (interval %ss)", options['interval'])
        while True:
            close_old_connections()
            try:
                stats = agenda_service().run()
                if stats:
                    logger.info("Pass: %s", stats)
            except Exception:
                logger.exception("Agenda worker pass failed")
            if options['once']:
                break
            time.sleep(options['interval'])
