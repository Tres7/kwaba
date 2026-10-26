"""Containers needed by the tests, started only when a test needs them.

- A test without a database (tests/unit) starts nothing.
- The first test that touches the database starts `postgres-test` (compose.test.yaml), then stops it at the end
  of the session if it was not already running.
- TEST_SERVICES=external: the services are provided elsewhere (CI, local PostgreSQL) through POSTGRES_HOST, etc.
- TEST_KEEP_SERVICES=1: leaves the containers running to chain runs faster.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

COMPOSE_FILE = Path(__file__).resolve().parents[2] / 'compose.test.yaml'

POSTGRES = {
    'service': 'postgres-test',
    'settings': {'HOST': '127.0.0.1', 'PORT': '55432', 'NAME': 'kwaba', 'USER': 'kwaba',
                 'PASSWORD': 'kwaba-test'},
}


def externally_provided() -> bool:
    return os.getenv('TEST_SERVICES') == 'external'


def _compose(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(['docker', 'compose', '-f', str(COMPOSE_FILE), *args],
                          capture_output=True, text=True, check=check)


def _is_running(service: str) -> bool:
    return bool(_compose('ps', '--status', 'running', '--quiet', service, check=False).stdout.strip())


def start(service: str) -> bool:
    """Starts the service and waits for its healthcheck. Returns True if we started it."""
    if shutil.which('docker') is None:
        pytest.exit(
            "Docker est introuvable : impossible de démarrer les services de test. "
            "Installez Docker (ou activez l'intégration WSL de Docker Desktop), ou fournissez PostgreSQL "
            "vous-même avec TEST_SERVICES=external et POSTGRES_HOST / POSTGRES_PORT.",
            returncode=pytest.ExitCode.USAGE_ERROR,
        )
    if _is_running(service):
        return False
    result = _compose('up', '--detach', '--wait', service, check=False)
    if result.returncode != 0:
        pytest.exit(f'Démarrage de {service} impossible :\n{result.stderr}', returncode=pytest.ExitCode.USAGE_ERROR)
    return True


def stop(service: str) -> None:
    if os.getenv('TEST_KEEP_SERVICES') != '1':
        _compose('rm', '--stop', '--force', service, check=False)
