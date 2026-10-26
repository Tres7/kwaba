from config import health


def test_health_ok(api_client):
    response = api_client.get('/api/health/')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_health_reports_unavailable_database(api_client, monkeypatch):
    class UnreachableDatabase:
        def cursor(self):
            raise ConnectionError('base injoignable')

    monkeypatch.setattr(health, 'connection', UnreachableDatabase())
    response = api_client.get('/api/health/')
    assert response.status_code == 503
    assert response.json()['database'] == 'unavailable'


def test_health_is_exempt_from_https_redirect(api_client, settings):
    # Render's probe arrives over internal HTTP: it must not be redirected to HTTPS
    settings.SECURE_SSL_REDIRECT = True
    assert api_client.get('/api/health/').status_code == 200
    assert api_client.get('/api/v1/hebergements/').status_code == 301
