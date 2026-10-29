from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reservations'
    label = 'reservations'

    def ready(self):
        from apps.documents.api import enregistrer
        from apps.hebergements.api import enregistrer_reservations
        from apps.paiements.api import enregistrer_produit

        from .documents import PRODUIT
        from .occupations import FOURNISSEUR
        from .paiement import PRODUIT_PAYE

        enregistrer(PRODUIT)
        enregistrer_produit(PRODUIT_PAYE)
        enregistrer_reservations(FOURNISSEUR)
