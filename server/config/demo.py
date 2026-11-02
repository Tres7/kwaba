"""Demo data (seed_demo, seed_give_demo): fictional content and accounts whose password is in this public repository.

Allowed locally and on the preprod. In production, the listings would be public and the accounts open to anyone.
"""
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import CommandError

HOTES_PRODUCTION = ('kwa-ba.com', 'www.kwa-ba.com')


def refuser_en_production() -> None:
    if urlsplit(settings.FRONTEND_URL).hostname in HOTES_PRODUCTION:
        raise CommandError("Données de démonstration refusées : FRONTEND_URL désigne la production.")
