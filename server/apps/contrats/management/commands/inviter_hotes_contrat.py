from django.core.management.base import BaseCommand, CommandError

from apps.contrats.services import inviter_hotes_a_signer
from apps.documents.api import societe_immatriculee


class Command(BaseCommand):
    help = "Envoie de nouveau l'invitation à signer le contrat aux hôtes qui ne l'ont pas encore signé."

    def handle(self, *args, **options):
        # Sent automatically when RCCM and NIF are filled in (back-office); this command is for a manual reminder
        if not societe_immatriculee():
            raise CommandError("Renseignez d'abord le RCCM et le NIF de la société (back-office) : le contrat n'est pas encore disponible.")
        self.stdout.write(f"Invitations envoyées : {inviter_hotes_a_signer()}")
