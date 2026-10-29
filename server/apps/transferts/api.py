from datetime import datetime
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from . import services, tarifs
from .models import AeroportModel, ChauffeurModel, TransfertModel


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


def _fiche(c: ChauffeurModel) -> dict:
    return {'id': c.pk, 'prenom': c.prenom, 'nom': c.nom, 'telephone': c.telephone, 'email': c.email,
            'excellence': c.excellence, 'actif': c.actif, 'pays_versement': c.pays_versement,
            'operateur_versement': c.operateur_versement, 'numero_versement': c.numero_versement}


def fiche_chauffeur(chauffeur_id) -> dict | None:
    """A partner driver (rentals with a driver), active or not; None if unknown or invalid id."""
    try:
        c = ChauffeurModel.objects.filter(pk=int(chauffeur_id)).first()
    except (TypeError, ValueError):
        return None
    return _fiche(c) if c else None


def fiches_chauffeurs(chauffeur_ids) -> dict[int, dict]:
    return {c.pk: _fiche(c) for c in ChauffeurModel.objects.filter(pk__in=[i for i in chauffeur_ids if i])}


def chauffeurs_actifs() -> list[dict]:
    return [_fiche(c) for c in ChauffeurModel.objects.filter(actif=True).order_by('prenom')]


def chauffeurs_des_transferts_termines(voyageur_id) -> set[int]:
    return set(TransfertModel.objects.filter(voyageur_id=voyageur_id, statut='termine', chauffeur_id__isnull=False)
               .values_list('chauffeur_id', flat=True))
