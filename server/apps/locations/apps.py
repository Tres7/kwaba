from django.apps import AppConfig


class LocationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.locations'
    label = 'locations'
    verbose_name = 'Location de voitures'

    def ready(self):
        from apps.documents.api import enregistrer

        from .documents import PRODUIT

        enregistrer(PRODUIT)
