"""Django check (`manage.py check --database default`, and every `migrate`, hence every deployment): an open module
must not write to an inactive offer or nature, or its payments would be refused by the ledger (ADR-024)."""
from django.core import checks
from django.db import connection

from apps.finance.application.registre import ECRIVAINS
from apps.finance.domain.rules import ecarts_des_modules_ouverts
from apps.finance.infrastructure.persistence.restitutions import SqlRestitutions


@checks.register(checks.Tags.database)
def modules_ouverts_et_referentiel(app_configs=None, databases=None, **kwargs):
    if not databases or not ECRIVAINS:
        return []
    # First deployment: the tables of the module do not exist yet, nothing to compare
    if not {'finance_offre', 'finance_nature'} <= set(connection.introspection.table_names()):
        return []
    offres, natures = SqlRestitutions().codes_actifs()
    return [checks.Error(ecart, id='finance.E001',
                         hint="Activer l'offre ou la nature dans le référentiel finance, ou fermer le module.")
            for ecart in ecarts_des_modules_ouverts(ECRIVAINS.values(), offres, natures)]
