from django.apps import AppConfig


class VerificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.verifications'
    label = 'verifications'
    verbose_name = 'Vérification des hôtes'

    def ready(self):
        from apps.terrain.api import enregistrer

        from .missions import TYPES_MISSIONS

        for type_mission in TYPES_MISSIONS:
            enregistrer(type_mission)
