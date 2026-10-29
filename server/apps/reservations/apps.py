from django.apps import AppConfig


class ReservationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reservations'
    label = 'reservations'

    def ready(self):
        from apps.documents.api import enregistrer

        from .documents import PRODUIT

        enregistrer(PRODUIT)
