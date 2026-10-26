import pytest
import requests

from apps.users.infrastructure.external.GoogleAPITokenVerifier import GoogleAPITokenVerifier

KWABA_CLIENT_ID = 'kwaba-web.apps.googleusercontent.com'


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code, self._payload = status_code, payload

    def json(self):
        return self._payload


def _tokeninfo(**overrides):
    return {
        'aud': KWABA_CLIENT_ID,
        'iss': 'https://accounts.google.com',
        'sub': 'google-123',
        'email': 'ama@example.tg',
        'email_verified': 'true',
        'given_name': 'Ama',
        'family_name': 'Kossi',
        **overrides,
    }


@pytest.fixture
def google(monkeypatch):
    """Replaces the call to Google: `google.reply(...)` sets the response, `google.calls` keeps the calls."""
    class Google:
        calls = []
        response = FakeResponse(200, _tokeninfo())
        error = None

        def reply(self, status_code=200, **payload):
            self.response = FakeResponse(status_code, _tokeninfo(**payload))

    fake = Google()

    def fake_get(url, **kwargs):
        fake.calls.append(kwargs)
        if fake.error:
            raise fake.error
        return fake.response

    monkeypatch.setattr(requests, 'get', fake_get)
    return fake


def verifier():
    return GoogleAPITokenVerifier(client_ids=[KWABA_CLIENT_ID])


def test_token_issued_for_kwaba_is_accepted(google):
    info = verifier().verify('jeton')
    assert (info.google_id, info.email, info.email_verified) == ('google-123', 'ama@example.tg', True)
    assert google.calls[0]['timeout'] == 5


def test_token_issued_for_another_application_is_rejected(google):
    # A third-party site replays the token a visitor gave it when signing in with Google
    google.reply(aud='site-tiers.apps.googleusercontent.com')
    with pytest.raises(ValueError, match='invalide'):
        verifier().verify('jeton')


@pytest.mark.parametrize('iss', ['https://evil.example', None])
def test_token_from_another_issuer_is_rejected(google, iss):
    google.reply(iss=iss)
    with pytest.raises(ValueError, match='invalide'):
        verifier().verify('jeton')


def test_invalid_or_expired_token_rejected(google):
    google.reply(status_code=400)
    with pytest.raises(ValueError, match='invalide'):
        verifier().verify('jeton')


@pytest.mark.parametrize('error', [requests.Timeout(), requests.ConnectionError()])
def test_google_unreachable(google, error):
    google.error = error
    with pytest.raises(ValueError, match='injoignable'):
        verifier().verify('jeton')


def test_disabled_without_configured_client_id(google):
    with pytest.raises(ValueError, match="n'est pas disponible"):
        GoogleAPITokenVerifier(client_ids=[]).verify('jeton')
    assert google.calls == []


def test_several_client_ids_accepted(google):
    google.reply(aud='kwaba-mobile.apps.googleusercontent.com')
    GoogleAPITokenVerifier(client_ids=[KWABA_CLIENT_ID, 'kwaba-mobile.apps.googleusercontent.com']).verify('jeton')


def test_client_ids_read_from_settings(google, settings):
    settings.GOOGLE_CLIENT_IDS = [KWABA_CLIENT_ID]
    assert GoogleAPITokenVerifier().verify('jeton').email == 'ama@example.tg'
