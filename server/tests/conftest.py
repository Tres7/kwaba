from pathlib import Path

import pytest

from tests import services

_TESTS_DIR = Path(__file__).parent
_MARKERS = ('unit', 'integration', 'broker')


def pytest_collection_modifyitems(config, items):
    """Sets the unit / integration / broker marker from the test's folder.

    A test of tests/unit that would touch the database fails by itself:
    pytest-django refuses access without the django_db marker.
    """
    for item in items:
        layer = Path(item.fspath).relative_to(_TESTS_DIR).parts[0]
        if layer not in _MARKERS:
            raise pytest.UsageError(f'{item.nodeid} : les tests vont dans tests/unit, tests/integration ou tests/broker')
        item.add_marker(getattr(pytest.mark, layer))


@pytest.fixture(scope='session')
def django_db_modify_db_settings(django_db_modify_db_settings_parallel_suffix):
    """Called by pytest-django right before creating the test database, so only if a test touches the database.

    Then starts the test PostgreSQL container (see tests/services.py) and points Django to it.
    """
    if services.externally_provided():
        yield
        return

    from django.conf import settings

    started = services.start(services.POSTGRES['service'])
    # In-place change: connections already created share this dictionary
    settings.DATABASES['default'].update(services.POSTGRES['settings'])
    yield
    if started:
        services.stop(services.POSTGRES['service'])


@pytest.fixture(autouse=True)
def _http_test_client(settings):
    # The test client speaks HTTP: without this, the production HTTPS redirect would return 301s
    settings.SECURE_SSL_REDIRECT = False


@pytest.fixture(autouse=True)
def _modules_affiches(settings):
    # A module's tests assume it is displayed; the hidden launch state has its own tests (tests/integration/site)
    settings.MODULES = {nom: True for nom in settings.MODULES}
