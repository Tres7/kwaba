import os
import subprocess
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[3]


def _load_settings(**env):
    """Loads config.settings in a fresh process, without server/.env nor inherited variables."""
    code = 'import config.settings as s; print(s.DEBUG, s.SECURE_SSL_REDIRECT if hasattr(s, "SECURE_SSL_REDIRECT") else None)'
    base = {'PATH': os.environ['PATH'], 'PYTHONPATH': str(SERVER_DIR)}
    # dotenv does not override an already defined variable: an empty value neutralises server/.env
    neutral = {name: '' for name in ('DJANGO_SECRET_KEY', 'DJANGO_DEBUG', 'R2_BUCKET', 'POSTGRES_PASSWORD')}
    return subprocess.run([sys.executable, '-c', code], cwd=SERVER_DIR, env={**base, **neutral, **env},
                          capture_output=True, text=True)


def test_production_refuses_to_start_without_secret_key():
    result = _load_settings()
    assert result.returncode != 0
    assert 'DJANGO_SECRET_KEY est obligatoire' in result.stderr


def test_debug_is_off_and_https_enforced_by_default():
    result = _load_settings(DJANGO_SECRET_KEY='x' * 50, POSTGRES_PASSWORD='p')
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ['False', 'True']


def test_development_runs_without_secret_key():
    result = _load_settings(DJANGO_DEBUG='True')
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ['True', 'None']


def test_production_refuses_to_start_without_database_password():
    """No default PostgreSQL password outside development: a forgotten variable must not open the database."""
    result = _load_settings(DJANGO_SECRET_KEY='x' * 50)
    assert result.returncode != 0
    assert 'POSTGRES_PASSWORD est obligatoire' in result.stderr
