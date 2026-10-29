import uuid

from .models import FavoriModel


def ids_favoris(user_id: uuid.UUID) -> set[uuid.UUID]:
    return set(FavoriModel.objects.filter(user_id=user_id).values_list('hebergement_id', flat=True))
