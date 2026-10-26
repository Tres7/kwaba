from collections.abc import Iterable

import requests
from django.conf import settings

from apps.users.application.ports.GoogleTokenVerifier import GoogleTokenVerifier, GoogleUserInfo

INVALID_TOKEN = "Token Google invalide ou expiré."


class GoogleAPITokenVerifier(GoogleTokenVerifier):

    _URL = "https://oauth2.googleapis.com/tokeninfo"
    _ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
    _TIMEOUT_SECONDS = 5

    def __init__(self, client_ids: Iterable[str] | None = None):
        self._client_ids = set(settings.GOOGLE_CLIENT_IDS if client_ids is None else client_ids)

    def verify(self, id_token: str) -> GoogleUserInfo:
        if not self._client_ids:
            raise ValueError("La connexion avec Google n'est pas disponible.")

        try:
            response = requests.get(self._URL, params={"id_token": id_token}, timeout=self._TIMEOUT_SECONDS)
        except requests.RequestException:
            raise ValueError("Google est injoignable, réessayez dans un instant.")
        if response.status_code != 200:
            raise ValueError(INVALID_TOKEN)

        data = response.json()
        # The token must have been issued for Kwa-Ba: otherwise, a third-party site offering "Sign in with Google"
        # could replay its visitors' token here and open their Kwa-Ba account. Same message, on purpose.
        if data.get("aud") not in self._client_ids or data.get("iss") not in self._ISSUERS:
            raise ValueError(INVALID_TOKEN)

        return GoogleUserInfo(
            google_id=data['sub'],
            email=data['email'],
            first_name=data.get('given_name', ''),
            last_name=data.get('family_name', ''),
            avatar_url=data.get('picture'),
            email_verified=str(data.get('email_verified', 'false')).lower() == 'true',
        )
