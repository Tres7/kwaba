"""Cloudflare Turnstile captcha at sign-in and sign-up."""
import pytest
import requests

from apps.securite import captcha

LOGIN = '/api/v1/auth/login/'
REGISTER = '/api/v1/auth/register/'


class FausseReponse:
    def __init__(self, succes):
        self.succes = succes

    def raise_for_status(self):
        pass

    def json(self):
        return {'success': self.succes}


@pytest.fixture
def turnstile(settings, monkeypatch):
    """Captcha active; Cloudflare only accepts the "good" token."""
    settings.TURNSTILE_SITE_KEY, settings.TURNSTILE_SECRET_KEY = 'site', 'secret'
    appels = []

    def poster(url, data, timeout):
        appels.append(data)
        return FausseReponse(data['response'] == 'bon')

    monkeypatch.setattr(captcha.requests, 'post', poster)
    return appels


def _inscription(**extra):
    return {'email': 'nouveau@test.tg', 'first_name': 'Ama', 'last_name': 'Koffi',
            'password': 'Kwaba-Test-2026!', 'password_confirm': 'Kwaba-Test-2026!', **extra}


def test_cle_publique_exposee_seulement_si_actif(api_client, settings):
    settings.TURNSTILE_SITE_KEY, settings.TURNSTILE_SECRET_KEY = 'site', ''
    assert api_client.get('/api/v1/auth/captcha/').data == {'site_key': ''}
    settings.TURNSTILE_SECRET_KEY = 'secret'
    assert api_client.get('/api/v1/auth/captcha/').data == {'site_key': 'site'}


def test_connexion_refusee_sans_captcha_valide(api_client, make_user, password, turnstile):
    user = make_user()
    for jeton in (None, 'mauvais'):
        corps = {'email': user.email, 'password': password, **({'captcha': jeton} if jeton else {})}
        reponse = api_client.post(LOGIN, corps, format='json')
        assert reponse.status_code == 400 and reponse.data['code'] == 'captcha'
    assert api_client.post(LOGIN, {'email': user.email, 'password': password, 'captcha': 'bon'},
                           format='json').status_code == 200
    assert turnstile[-1] == {'secret': 'secret', 'response': 'bon'}


def test_inscription_refusee_sans_captcha_valide(api_client, turnstile):
    reponse = api_client.post(REGISTER, _inscription(), format='json')
    assert reponse.status_code == 400 and reponse.data['code'] == 'captcha'
    assert api_client.post(REGISTER, _inscription(captcha='bon'), format='json').status_code == 201


def test_cloudflare_injoignable_ne_bloque_pas_la_connexion(api_client, make_user, password, settings, monkeypatch):
    settings.TURNSTILE_SITE_KEY, settings.TURNSTILE_SECRET_KEY = 'site', 'secret'

    def panne(*args, **kwargs):
        raise requests.ConnectionError('injoignable')

    monkeypatch.setattr(captcha.requests, 'post', panne)
    user = make_user()
    assert api_client.post(LOGIN, {'email': user.email, 'password': password, 'captcha': 'x'},
                           format='json').status_code == 200


def test_desactive_sans_cle(api_client, make_user, password):
    user = make_user()
    assert api_client.post(LOGIN, {'email': user.email, 'password': password}, format='json').status_code == 200
