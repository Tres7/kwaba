from datetime import datetime

from django.utils import timezone

from . import services, tarifs
from .models import AeroportModel


def aeroports_ouverts() -> list[dict]:
    return [{'code': a.code, 'nom': a.nom, 'ville': a.ville} for a in AeroportModel.objects.filter(actif=True)]


def devis(code_aeroport: str, arrivee_naive: datetime, passagers: int, bagages: int) -> dict | None:
    aeroport = AeroportModel.objects.filter(pk=code_aeroport, actif=True).first()
    if not aeroport:
        return None
    arrivee = services.heure_locale(aeroport, arrivee_naive)
    return {
        'aeroport': {'code': aeroport.code, 'nom': aeroport.nom, 'ville': aeroport.ville},
        'options': services.devis(aeroport, arrivee, passagers, bagages),
        'trop_tard': arrivee - timezone.now() < tarifs.DELAI_MIN_RESERVATION,
    }
