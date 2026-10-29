import uuid
from collections.abc import Iterable

from .models import HebergementModel
from .serializers import HebergementSerializer


def est_publiee(hebergement_id: uuid.UUID) -> bool:
    return HebergementModel.objects.publiees().filter(pk=hebergement_id).exists()


def cartes(hebergement_ids: Iterable[uuid.UUID], request=None) -> dict[uuid.UUID, dict]:
    annonces = (HebergementModel.objects.publiees().filter(pk__in=list(hebergement_ids))
                .select_related('host', 'host__piece_identite'))
    donnees = HebergementSerializer(annonces, many=True, context={'request': request}).data
    return {uuid.UUID(carte['id']): carte for carte in donnees}
