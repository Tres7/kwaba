from .models import ParametresLocationModel, PartenaireLocationModel


def _partie(p: PartenaireLocationModel) -> dict:
    return {'id': p.pk, 'nom': p.nom, 'email': p.email, 'telephone': p.telephone,
            'details': f"représenté par {p.contact}," if p.contact else ''}


def loueur(loueur_id) -> dict | None:
    try:
        p = PartenaireLocationModel.objects.filter(pk=int(loueur_id)).first()
    except (TypeError, ValueError):
        return None
    return _partie(p) if p else None


def loueurs(q: str = '', limite: int = 30) -> list[dict]:
    qs = PartenaireLocationModel.objects.filter(actif=True)
    if q:
        qs = qs.filter(nom__icontains=q)
    return [_partie(p) for p in qs.order_by('nom')[:limite]]


def parametres_contrat() -> dict | None:
    p = ParametresLocationModel.objects.first()
    if not p:
        return None
    return {'commission_pourcent': p.commission_pourcent, 'delai_min_jours': p.delai_min_jours,
            'restitution_caution_heures': p.restitution_caution_heures}
