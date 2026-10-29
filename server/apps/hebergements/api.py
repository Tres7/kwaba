import uuid
from collections.abc import Iterable
from datetime import date

from django.db.models import Count, Q
from django.utils import timezone

from . import disponibilites
from . import occupations
from .occupations import FournisseurReservations as FournisseurReservations
from . import types_logement
from .models import HebergementModel, TypeLogementModel
from .serializers import HebergementSerializer


def est_publiee(hebergement_id: uuid.UUID) -> bool:
    return HebergementModel.objects.publiees().filter(pk=hebergement_id).exists()


def existe(hebergement_id: uuid.UUID) -> bool:
    return HebergementModel.objects.filter(pk=hebergement_id).exists()


def cartes(hebergement_ids: Iterable[uuid.UUID], request=None, publiees_seulement: bool = True) -> dict[uuid.UUID, dict]:
    qs = HebergementModel.objects.publiees() if publiees_seulement else HebergementModel.tous.all()
    annonces = qs.filter(pk__in=list(hebergement_ids)).select_related('host', 'host__piece_identite')
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


def ids_par_nom(texte: str) -> set[uuid.UUID]:
    return set(HebergementModel.tous.filter(name__icontains=texte).values_list('pk', flat=True))


def mettre_a_jour_note(hebergement_id: uuid.UUID, note: float, nombre_avis: int) -> None:
    HebergementModel.tous.filter(pk=hebergement_id).update(rating=round(note, 2), review_count=nombre_avis)


def _fiche(h: HebergementModel) -> dict:
    return {
        'id': h.id, 'name': h.name, 'type': h.type, 'type_libelle': h.get_type_display(), 'city': h.city,
        'location': h.location, 'description': h.description, 'price_per_night': h.price_per_night,
        'max_guests': h.max_guests, 'amenities': h.amenities, 'image_url': h.image_url, 'images': h.images,
        'created_at': h.created_at, 'host_id': h.host_id, 'statut_verification': h.statut_verification,
        'politique_annulation': h.politique_annulation, 'arrivee_a_partir': h.arrivee_a_partir,
        'depart_avant': h.depart_avant,
    }


def fiche(hebergement_id: uuid.UUID, archivees: bool = False) -> dict | None:
    """`archivees`: also an archived listing (history of a booking)."""
    qs = HebergementModel.tous if archivees else HebergementModel.objects
    h = qs.filter(pk=hebergement_id).first()
    return _fiche(h) if h else None


def annonces_en_attente(hote_ids: Iterable[uuid.UUID], ville: str = '') -> list[dict]:
    qs = HebergementModel.objects.filter(statut_verification='en_attente', host_id__in=list(hote_ids))
    if ville:
        qs = qs.filter(city__icontains=ville)
    return [_fiche(h) for h in qs.order_by('created_at')]


def nb_annonces_non_verifiees(hote_id: uuid.UUID) -> int:
    return HebergementModel.objects.filter(host_id=hote_id).exclude(statut_verification='verifiee').count()


def nb_annonces_par_hote(hote_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, int]:
    return dict(HebergementModel.objects.filter(host_id__in=list(hote_ids)).values('host_id')
                .annotate(n=Count('id')).values_list('host_id', 'n'))


def verrouiller_fiche(hebergement_id: uuid.UUID) -> dict | None:
    h = HebergementModel.objects.select_for_update().filter(pk=hebergement_id).first()
    return _fiche(h) if h else None


def enregistrer_verification(hebergement_id: uuid.UUID, verifiee: bool, motif: str = '') -> None:
    maintenant = timezone.now()
    if verifiee:
        HebergementModel.objects.filter(pk=hebergement_id).update(
            statut_verification='verifiee', verifiee_le=maintenant, motif_refus='', updated_at=maintenant)
    else:
        HebergementModel.objects.filter(pk=hebergement_id).update(
            statut_verification='refusee', motif_refus=motif, updated_at=maintenant)


def enregistrer_reservations(fournisseur: FournisseurReservations) -> None:
    occupations.enregistrer(fournisseur)


def ids_annonces_de(hote_id) -> set[uuid.UUID]:
    """The host's listings, archived ones included (their bookings stay in the history)."""
    return set(HebergementModel.tous.filter(host_id=hote_id).values_list('pk', flat=True))


def hotes_des_annonces(hebergement_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, uuid.UUID]:
    return dict(HebergementModel.tous.filter(pk__in=list(hebergement_ids)).values_list('pk', 'host_id'))


def _fiche_type(t: TypeLogementModel) -> dict:
    return {'id': t.id, 'hebergement_id': t.hebergement_id, 'nom': t.nom, 'capacite': t.capacite,
            'prix_nuit': t.prix_nuit, 'quantite': t.quantite, 'actif': t.actif}


def fiche_type(type_logement_id) -> dict | None:
    t = TypeLogementModel.objects.filter(pk=type_logement_id).first()
    return _fiche_type(t) if t else None


def type_par_defaut(hebergement_id) -> dict:
    """The unit type booked when none is chosen (created if missing)."""
    return fiche_type(types_logement.type_par_defaut_id(hebergement_id))


def noms_types(type_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, str]:
    return dict(TypeLogementModel.objects.filter(pk__in=[i for i in type_ids if i]).values_list('pk', 'nom'))


def verrouiller_types(type_ids) -> None:
    disponibilites.verrouiller_types(type_ids)


def verrouiller(hebergement_id) -> None:
    disponibilites.verrouiller(hebergement_id)


def conflit(hebergement_id, debut: date, fin: date, exclure=None, type_logement_id=None, nb: int = 1) -> str | None:
    """Why `nb` units of the type (default type if none) cannot be booked over the period, or None."""
    type_logement = TypeLogementModel.objects.get(pk=type_logement_id) if type_logement_id else None
    return disponibilites.conflit(hebergement_id, debut, fin, exclure=exclure, type_logement=type_logement, nb=nb)
