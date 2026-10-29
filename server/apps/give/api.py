import uuid

from . import montants
from .models import OrganisationModel


def _partie(o: OrganisationModel) -> dict:
    precisions = [f"association enregistrée sous le n° {o.numero_enregistrement}" if o.numero_enregistrement else '',
                  f"représentée par {o.contact_nom}" if o.contact_nom else '']
    return {'id': o.pk, 'nom': o.nom, 'email': o.contact_email, 'telephone': o.contact_telephone,
            'details': ''.join(f"{x}, " for x in precisions if x).strip()}


def organisation(organisation_id) -> dict | None:
    try:
        o = OrganisationModel.objects.filter(pk=uuid.UUID(str(organisation_id))).first()
    except (TypeError, ValueError):
        return None
    return _partie(o) if o else None


def organisations(q: str = '', limite: int = 30) -> list[dict]:
    qs = OrganisationModel.objects.all()
    if q:
        qs = qs.filter(nom__icontains=q)
    return [_partie(o) for o in qs.order_by('nom')[:limite]]


def jour_reversement() -> int:
    return montants.JOUR_REVERSEMENT
