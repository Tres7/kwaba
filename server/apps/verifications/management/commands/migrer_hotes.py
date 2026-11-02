from django.core.management.base import BaseCommand

from apps.contrats import api as contrats
from apps.hebergements import api as hebergements
from apps.securite.audit import journaliser
from apps.users import api as users
from apps.verifications.models import PieceIdentiteModel


class Command(BaseCommand):
    help = ("Applique la règle « hôte = au moins une annonce validée » aux comptes créés avant les candidatures. "
            "Sans --appliquer, affiche seulement ce qui changerait.")

    def add_arguments(self, parser):
        parser.add_argument('--appliquer', action='store_true', help='Écrit les changements (simulation par défaut).')

    def handle(self, *args, appliquer=False, **options):
        valides = hebergements.ids_hotes_avec_annonce_validee()
        commences = (hebergements.ids_hotes_avec_annonce() | hebergements.ids_hotes_avec_brouillon()
                     | contrats.ids_preinscrits() | set(PieceIdentiteModel.objects.values_list('hote_id', flat=True)))

        gardes = candidats = voyageurs = 0
        for hote in users.comptes_de_role('hote'):
            if hote.id in valides:
                gardes += 1
                continue
            candidature = hote.id in commences
            candidats += candidature
            voyageurs += not candidature
            self.stdout.write(f"{hote.email} : voyageur{', candidature ouverte' if candidature else ''}")
            if appliquer and users.retirer_role_hote(hote.id, candidature):
                journaliser('role_modifie', utilisateur=hote.id, email=hote.email, avant='hote', apres='voyageur',
                            candidature=candidature)

        bilan = f"{gardes} hôte(s) gardé(s), {candidats} candidat(s), {voyageurs} repassé(s) voyageur."
        if appliquer:
            journaliser('roles_hotes_migres', gardes=gardes, candidats=candidats, voyageurs=voyageurs)
            self.stdout.write(self.style.SUCCESS(f"{bilan} Changements écrits."))
        else:
            self.stdout.write(self.style.WARNING(f"{bilan} Simulation : relancer avec --appliquer pour écrire."))
