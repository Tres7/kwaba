from django.core.management.base import BaseCommand

from apps.activity.infrastructure.container import activity_service


class Command(BaseCommand):
    help = "Deletes the activity log entries older than 12 months, except those under a legal hold."

    def handle(self, *args, **options):
        deleted = activity_service().purge()
        self.stdout.write(f"{deleted} activity log entries deleted.")
