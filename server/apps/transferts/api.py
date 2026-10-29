from datetime import datetime
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from . import services, tarifs
from .models import AeroportModel, ChauffeurModel


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


def _partie(c: ChauffeurModel) -> dict:
    return {'id': c.pk, 'nom': f"{c.prenom} {c.nom}", 'email': c.email, 'telephone': c.telephone,
            'details': f"chauffeur, véhicule {c.vehicule} immatriculé {c.immatriculation},"}


def chauffeur(chauffeur_id) -> dict | None:
    try:
        c = ChauffeurModel.objects.filter(pk=int(chauffeur_id)).first()
    except (TypeError, ValueError):
        return None
    return _partie(c) if c else None


def chauffeurs(q: str = '', limite: int = 30) -> list[dict]:
    qs = ChauffeurModel.objects.filter(actif=True)
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(prenom__icontains=q))
    return [_partie(c) for c in qs.order_by('prenom')[:limite]]


def commission_chauffeur() -> Decimal:
    return tarifs.COMMISSION_CHAUFFEUR
