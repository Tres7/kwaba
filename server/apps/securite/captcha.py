"""Cloudflare Turnstile captcha: sign-in and sign-up.

The browser gets a token from the widget (checkbox, often validated without a click); the server has it
confirmed by Cloudflare. Without TURNSTILE_SECRET_KEY (development, tests), the captcha is disabled.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger('apps.securite')

URL_VERIFICATION = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
MESSAGE = 'Confirmez que vous n\'êtes pas un robot (case à cocher), puis réessayez.'


def actif() -> bool:
    return bool(settings.TURNSTILE_SECRET_KEY and settings.TURNSTILE_SITE_KEY)


def valide(jeton) -> bool:
    """True if Cloudflare confirms the token (single use). Captcha disabled: always True.

    Cloudflare unreachable: let it through (logged) rather than blocking every sign-in; the attempt and rate
    limits still apply.
    """
    if not actif():
        return True
    if not jeton or not isinstance(jeton, str) or len(jeton) > 2048:
        return False
    # No remoteip: the sign-in goes through the Next.js server, whose address is not the visitor's
    donnees = {'secret': settings.TURNSTILE_SECRET_KEY, 'response': jeton}
    try:
        reponse = requests.post(URL_VERIFICATION, data=donnees, timeout=5)
        reponse.raise_for_status()
        return bool(reponse.json().get('success'))
    except (requests.RequestException, ValueError):
        logger.warning('Turnstile injoignable : captcha non vérifié', exc_info=True)
        return True
