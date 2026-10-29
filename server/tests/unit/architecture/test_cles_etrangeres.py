"""No foreign key between modules (ADR-019): a module keeps the other module's id. import-linter does not see them."""
from django.apps import apps


def _modules():
    return [config for config in apps.get_app_configs() if config.name.startswith('apps.')]


def _cles_entre_modules() -> list[str]:
    nos_modules = {config.label for config in _modules()}
    trouvees = []
    for config in _modules():
        for modele in config.get_models():
            for champ in modele._meta.get_fields():
                if not (champ.is_relation and champ.concrete) or champ.related_model is None:
                    continue
                cible = champ.related_model._meta.app_label
                if cible != config.label and cible in nos_modules:
                    trouvees.append(f'{modele._meta.label}.{champ.name} -> {champ.related_model._meta.label}')
    return trouvees


def test_the_scan_sees_the_modules():
    assert {'users', 'reservations', 'hebergements', 'paiements'} <= {config.label for config in _modules()}


def test_no_foreign_key_between_modules():
    assert _cles_entre_modules() == [], 'Gardez un identifiant (<objet>_id) et lisez-le via api.py du module'
