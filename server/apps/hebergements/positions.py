"""Position shown to travellers: never the real one, so that a host cannot be found without booking (anti-bypass).

The offset comes from the listing's id and a secret: it never changes, so comparing answers reveals nothing, and it
cannot be computed back. The real position stays within ZONE_M of the shown one: the listing page draws this zone.
"""
import hashlib
import hmac
import math

from django.conf import settings

DISTANCE_MIN_M = 150
ZONE_M = 400
METRES_PAR_DEGRE = 111_320


def approchee(hebergement) -> dict | None:
    """{'lat': …, 'lng': …, 'rayon_m': …}, or None for an older listing without a position."""
    if hebergement.latitude is None or hebergement.longitude is None:
        return None
    graine = hmac.new(settings.SECRET_KEY.encode(), str(hebergement.pk).encode(), hashlib.sha256).digest()
    angle = int.from_bytes(graine[:4], 'big') / 2 ** 32 * math.tau
    distance = DISTANCE_MIN_M + int.from_bytes(graine[4:8], 'big') / 2 ** 32 * (ZONE_M - DISTANCE_MIN_M)
    latitude, longitude = float(hebergement.latitude), float(hebergement.longitude)
    return {
        'lat': round(latitude + distance * math.cos(angle) / METRES_PAR_DEGRE, 5),
        'lng': round(longitude + distance * math.sin(angle) / (METRES_PAR_DEGRE * math.cos(math.radians(latitude))), 5),
        'rayon_m': ZONE_M,
    }
