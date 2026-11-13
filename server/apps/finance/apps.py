from django.apps import AppConfig
from django.db.models.signals import post_migrate, pre_migrate


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.finance'
    verbose_name = 'Finance (grand livre des mouvements)'

    def ready(self):
        from apps.finance.infrastructure import checks  # noqa: F401 (registers the system check)
        from apps.finance.infrastructure.persistence import sql_restitutions

        # Reporting views and functions: dropped before every migrate, created again after (ADR-024)
        pre_migrate.connect(sql_restitutions.avant_migration, sender=self, dispatch_uid='finance.vues.avant')
        post_migrate.connect(sql_restitutions.apres_migration, sender=self, dispatch_uid='finance.vues.apres')
