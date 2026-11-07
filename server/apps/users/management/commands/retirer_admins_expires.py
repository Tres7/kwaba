from django.core.management.base import BaseCommand

from apps.users.admins import retirer_expires


class Command(BaseCommand):
    help = "Temporary admins past their end date go back to their previous role."

    def handle(self, *args, **options):
        self.stdout.write(f"{retirer_expires()} admin(s) temporaire(s) retiré(s).")
