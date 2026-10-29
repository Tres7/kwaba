import uuid
from collections.abc import Iterable
from datetime import date

from django.db.models import Q

from . import disponibilites
from .models import HebergementModel
from .serializers import HebergementSerializer


def est_publiee(hebergement_id: uuid.UUID) -> bool:
    return HebergementModel.objects.publiees().filter(pk=hebergement_id).exists()


def cartes(hebergement_ids: Iterable[uuid.UUID], request=None) -> dict[uuid.UUID, dict]:
    annonces = (HebergementModel.objects.publiees().filter(pk__in=list(hebergement_ids))
                .select_related('host', 'host__piece_identite'))
    donnees = HebergementSerializer(annonces, many=True, context={'request': request}).data
    return {uuid.UUID(carte['id']): carte for carte in donnees}


def resumes(hebergement_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, dict]:
    ids = list(hebergement_ids)
    publiees = set(HebergementModel.objects.publiees().filter(pk__in=ids).values_list('pk', flat=True))
    return {h.id: {
        'id': h.id, 'name': h.name, 'host_id': h.host_id, 'city': h.city, 'location': h.location, 'type': h.type,
        'image_url': h.image_url, 'price_per_night': h.price_per_night, 'max_guests': h.max_guests, 'rating': h.rating,
        'review_count': h.review_count, 'publiee': h.id in publiees,
    } for h in HebergementModel.tous.filter(pk__in=ids)}


def est_disponible(hebergement_id: uuid.UUID, debut: date, fin: date) -> bool:
    return disponibilites.est_disponible(hebergement_id, debut, fin)


def rechercher(ville: str, voyageurs: int | None = None, prix_max_nuit: int | None = None, type_: str | None = None,
               limite: int = 20) -> list[dict]:
    qs = HebergementModel.objects.publiees().filter(Q(city__icontains=ville) | Q(location__icontains=ville))
    if voyageurs:
        qs = qs.filter(max_guests__gte=voyageurs)
    if prix_max_nuit:
        qs = qs.filter(price_per_night__lte=prix_max_nuit)
    if type_:
        qs = qs.filter(type=type_)
    return [{
        'id': h.id, 'name': h.name, 'type': h.type, 'city': h.city, 'location': h.location,
        'description': h.description, 'image_url': h.image_url, 'price_per_night': h.price_per_night,
        'rating': h.rating, 'review_count': h.review_count, 'max_guests': h.max_guests, 'amenities': h.amenities,
    } for h in qs.order_by('-rating', 'price_per_night')[:limite]]
