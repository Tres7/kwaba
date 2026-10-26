from datetime import date

from django.core.management.base import BaseCommand

from apps.give.models import OrganisationModel, ProjetModel

# Fictional NGOs, to try Kwa-Ba Give locally: never run this command in production
DEMO = [
    {
        'slug': 'demo-ecoles-du-mono', 'nom': 'Écoles du Mono (démo)', 'cause': 'education', 'pays': 'TG', 'ville': 'Aného',
        'resume': "Fournitures, cantine et soutien scolaire pour les écoles rurales du Mono.",
        'description': "Association fictive de démonstration.\n\nElle équipe chaque rentrée des écoles primaires rurales "
                       "et finance une cantine pour les enfants qui viennent de loin.",
        'projets': [('Rentrée 2026 : 300 kits scolaires', 'Aného', 1_500_000)],
    },
    {
        'slug': 'demo-puits-pour-tous', 'nom': 'Puits pour tous (démo)', 'cause': 'eau', 'pays': 'BJ', 'ville': 'Natitingou',
        'resume': "Forages et formation à l'entretien des pompes dans l'Atacora.",
        'description': "Association fictive de démonstration.\n\nChaque forage est confié à un comité villageois formé à son entretien.",
        'projets': [('Forage du village de Tanguiéta', 'Tanguiéta', 4_000_000)],
    },
    {
        'slug': 'demo-sante-sahel', 'nom': 'Santé Sahel (démo)', 'cause': 'sante', 'pays': 'BF', 'ville': 'Ouahigouya',
        'resume': "Consultations prénatales et médicaments essentiels dans les centres de santé ruraux.",
        'description': "Association fictive de démonstration.", 'projets': [],
    },
    {
        'slug': 'demo-cotes-vivantes', 'nom': 'Côtes vivantes (démo)', 'cause': 'environnement', 'pays': 'TG', 'ville': 'Lomé',
        'resume': "Nettoyage des plages et replantation de mangroves.",
        'description': "Association fictive de démonstration.", 'projets': [('10 000 palétuviers', 'Lac Togo', None)],
    },
]


class Command(BaseCommand):
    help = "Crée des ONG fictives pour essayer Kwa-Ba Give en local (idempotent)."

    def handle(self, *args, **options):
        for d in DEMO:
            champs = {k: v for k, v in d.items() if k != 'projets'}
            o, _ = OrganisationModel.objects.update_or_create(slug=d['slug'], defaults={
                **champs, 'numero_enregistrement': 'DÉMO-0000', 'verifiee_le': date.today(),
                'verification': "Organisation fictive créée pour la démonstration.",
            })
            for titre, lieu, objectif in d['projets']:
                ProjetModel.objects.update_or_create(organisation=o, titre=titre, defaults={
                    'cause': o.cause, 'lieu': lieu, 'objectif': objectif, 'resume': f"Projet de démonstration de {o.nom}.",
                })
        self.stdout.write(self.style.SUCCESS(f"{len(DEMO)} ONG de démonstration prêtes."))
