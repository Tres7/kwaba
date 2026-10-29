from django.apps import AppConfig


class TransfertsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.transferts'
    label = 'transferts'
    verbose_name = 'Transferts aéroport'

    def ready(self):
        from apps.documents.api import enregistrer

        from .documents import PRODUIT

        enregistrer(PRODUIT)
