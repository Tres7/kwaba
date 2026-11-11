from django.apps import AppConfig


class CorrecteurConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.correcteur'
    label = 'correcteur'
    verbose_name = 'Correcteur de fautes'
