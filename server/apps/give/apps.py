from django.apps import AppConfig


class GiveConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.give'
    label = 'give'
    verbose_name = 'Kwa-Ba Give (dons)'

    def ready(self):
        from apps.documents.api import enregistrer
        from apps.paiements.api import enregistrer_produit

        from .documents import PRODUIT
        from .paiement import PRODUIT_PAYE

        enregistrer(PRODUIT)
        enregistrer_produit(PRODUIT_PAYE)
