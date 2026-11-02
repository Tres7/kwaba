from types import SimpleNamespace
from unittest import mock

import pytest

from config.journal_gunicorn import JournalSansJeton, sans_jeton


@pytest.mark.parametrize('entree, attendu', [
    ('GET /api/v1/contrats/signature/jeton-secret/ HTTP/1.1', 'GET /api/v1/contrats/signature/***/ HTTP/1.1'),
    ('POST /api/v1/contrats/signature/jeton-secret/signer/ HTTP/1.1', 'POST /api/v1/contrats/signature/***/signer/ HTTP/1.1'),
    ('GET /api/v1/contrats/signature/jeton-secret?x=1 HTTP/1.1', 'GET /api/v1/contrats/signature/***?x=1 HTTP/1.1'),
    ('GET /api/v1/hebergements/ HTTP/1.1', 'GET /api/v1/hebergements/ HTTP/1.1'),
    ('GET /api/v1/admin/contrats/12/ HTTP/1.1', 'GET /api/v1/admin/contrats/12/ HTTP/1.1'),
])
def test_sans_jeton(entree, attendu):
    assert sans_jeton(entree) == attendu


def test_journal_d_acces_sans_jeton():
    chemin = '/api/v1/contrats/signature/jeton-secret/'
    journal = JournalSansJeton.__new__(JournalSansJeton)
    journal.cfg = SimpleNamespace(env_prefix='')
    environ = {
        'REQUEST_METHOD': 'GET', 'RAW_URI': chemin, 'SERVER_PROTOCOL': 'HTTP/1.1', 'PATH_INFO': chemin,
        'QUERY_STRING': '', 'HTTP_REFERER': f'https://kwa-ba.com{chemin}', 'HTTP_USER_AGENT': 'test', 'REMOTE_ADDR': '10.0.0.1',
    }
    reponse = SimpleNamespace(status='200 OK', status_code=200, sent=10, response_length=10, headers=[])
    requete = SimpleNamespace(headers=[])
    atomes = journal.atoms(reponse, requete, environ, mock.Mock(seconds=0, microseconds=1000, total_seconds=lambda: 0.001))
    assert 'jeton-secret' not in str(atomes['r'])
    assert 'jeton-secret' not in str(atomes['U'])
    assert 'jeton-secret' not in str(atomes['f'])
