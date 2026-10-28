from django.apps import AppConfig


class HebergementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hebergements'
    label = 'hebergements'

    def ready(self):
        from . import signals  # noqa: F401  (one unit type per establishment, kept in line with the listing)
