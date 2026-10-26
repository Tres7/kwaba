"""Rate limits and attempt counters, atomic (a single PostgreSQL query per increment)."""
import ipaddress
import random
from datetime import datetime

from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework.throttling import BaseThrottle

from .models import CompteurModel

_INCREMENTER = """
    INSERT INTO securite_compteur (cle, valeur, expire_le)
    VALUES (%s, 1, now() + make_interval(secs => %s))
    ON CONFLICT (cle) DO UPDATE SET
        valeur = CASE WHEN securite_compteur.expire_le <= now() THEN 1 ELSE securite_compteur.valeur + 1 END,
        expire_le = CASE WHEN securite_compteur.expire_le <= now() THEN EXCLUDED.expire_le
                         ELSE securite_compteur.expire_le END
    RETURNING valeur, expire_le
"""


def incrementer(cle: str, fenetre_secondes: int) -> tuple[int, datetime]:
    """Adds 1 to the `cle` counter (fixed window) and returns (new value, end of the window)."""
    with connection.cursor() as cursor:
        cursor.execute(_INCREMENTER, [cle[:200], fenetre_secondes])
        valeur, expire_le = cursor.fetchone()
    if random.random() < 0.01:
        # Occasional cleanup: expired counters are no longer useful
        CompteurModel.objects.filter(expire_le__lte=timezone.now()).delete()
    return valeur, expire_le


def reinitialiser(cle: str) -> None:
    CompteurModel.objects.filter(cle=cle[:200]).delete()


def secondes_restantes(expire_le: datetime) -> int:
    return max(1, int((expire_le - timezone.now()).total_seconds()) + 1)


def ip_client(request) -> str | None:
    """Client address. Behind N trusted proxies (DJANGO_NUM_PROXIES), the address added by the last proxy in
    X-Forwarded-For; without a proxy, REMOTE_ADDR (an X-Forwarded-For sent by the client is ignored)."""
    adresse = request.META.get('REMOTE_ADDR')
    proxys = settings.NUM_PROXIES
    transmis = request.META.get('HTTP_X_FORWARDED_FOR')
    if proxys and transmis:
        adresses = [a.strip() for a in transmis.split(',') if a.strip()]
        if adresses:
            adresse = adresses[-min(proxys, len(adresses))]
    try:
        return str(ipaddress.ip_address(adresse)) if adresse else None
    except ValueError:
        return None


def limite_ip(nom: str, nombre: int, secondes: int):
    """DRF throttle: at most `nombre` requests per IP address and per window of `secondes`."""

    class LimiteIP(BaseThrottle):
        def allow_request(self, request, view):
            if not settings.LIMITES_ACTIVES:
                return True
            valeur, expire_le = incrementer(f"ip:{nom}:{ip_client(request) or 'inconnue'}", secondes)
            self._attente = secondes_restantes(expire_le)
            return valeur <= nombre

        def wait(self):
            return getattr(self, '_attente', secondes)

    LimiteIP.__name__ = f"LimiteIP_{nom}"
    return LimiteIP


class Tentatives:
    """Attempt counter of a resource (email, code…): every try is counted BEFORE being checked,
    which makes the limit exact even with simultaneous requests. A success resets the counter."""

    def __init__(self, cle: str, maximum: int, fenetre_secondes: int):
        self.cle, self.maximum, self.fenetre = cle, maximum, fenetre_secondes
        self.attente = 0

    def essayer(self) -> bool:
        """Counts an attempt. False if the limit is exceeded (self.attente: seconds before trying again)."""
        if not settings.LIMITES_ACTIVES:
            return True
        valeur, expire_le = incrementer(self.cle, self.fenetre)
        self.attente = secondes_restantes(expire_le)
        return valeur <= self.maximum

    def reussite(self) -> None:
        reinitialiser(self.cle)
