"""Image URLs provided by users (avatar, listing photos).

An image shown to other users must only come from a known host: otherwise its author could put
the address of their own server and collect the IP address of every visitor (tracking pixel).
"""
from urllib.parse import urlsplit

from django.conf import settings

MESSAGE = "Image non autorisée : utilisez une photo envoyée sur Kwa-Ba."


def hote_autorise(hote: str) -> bool:
    hote = (hote or '').lower()
    for autorise in settings.IMAGES_HOTES_AUTORISES:
        if autorise.startswith('.'):
            if hote.endswith(autorise):
                return True
        elif hote == autorise:
            return True
    return False


def url_image_autorisee(url) -> bool:
    if not isinstance(url, str) or len(url) > 1000:
        return False
    try:
        morceaux = urlsplit(url.strip())
    except ValueError:
        return False
    schemas = ('https', 'http') if settings.DEBUG else ('https',)
    return morceaux.scheme in schemas and not morceaux.username and hote_autorise(morceaux.hostname)
