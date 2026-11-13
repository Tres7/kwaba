from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reservations'
    label = 'reservations'

    def ready(self):
        from apps.documents.api import enregistrer
        from apps.finance.api import declarer_ecritures
        from apps.hebergements.api import enregistrer_reservations
        from apps.paiements.api import enregistrer_produit

        from .documents import PRODUIT
        from .occupations import FOURNISSEUR
        from .paiement import PRODUIT_PAYE

        enregistrer(PRODUIT)
        enregistrer_produit(PRODUIT_PAYE)
        enregistrer_reservations(FOURNISSEUR)
        # Ledger (finance): what a stay writes; a deployment stops if one of them is inactive (check finance.E001)
        declarer_ecritures('sejours', offres={'COURTE_DUREE', 'HOTEL'},
                           natures={'T01', 'T02', 'T05', 'T09', 'R01', 'R02', 'R03', 'R08'})
