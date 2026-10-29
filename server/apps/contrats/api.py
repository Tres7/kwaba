import uuid
from collections.abc import Iterable

from . import preinscription
from django.db.models import Exists, OuterRef

from .models import ContratModel
from .services import ContratErreur, inviter_hotes_a_signer, signature_png

__all__ = ['ContratErreur', 'condition_contrat_signe', 'hote_a_signe', 'hotes_ayant_signe', 'inviter_hotes_a_signer', 'preinscription_requise',
           'signature_png']


def hote_a_signe(hote_id: uuid.UUID) -> bool:
    return ContratModel.objects.filter(hote_id=hote_id, statut='signe').exists()


def hotes_ayant_signe(hote_ids: Iterable[uuid.UUID], types: tuple[str, ...] = ('hote', 'hotel')) -> set[uuid.UUID]:
    return set(ContratModel.objects.filter(hote_id__in=list(hote_ids), type__in=types, statut='signe')
               .values_list('hote_id', flat=True))


def preinscription_requise(utilisateur) -> bool:
    return preinscription.requise(utilisateur)


def condition_contrat_signe(champ_hote: str = 'host') -> Exists:
    """SQL condition: the host (field `champ_hote` of the outer query) signed their agreement."""
    return Exists(ContratModel.objects.filter(hote=OuterRef(champ_hote), statut='signe'))
