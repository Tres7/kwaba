"""What field agents check, type by type.

Each type says where to find what waits for an agent (the "to do" queue), how to summarise it in a list and
detail it in its page. Decisions stay in the domain's application (verifications for listings and identity
documents): the mission only keeps their outcome.
"""
from dataclasses import dataclass
from typing import Callable

from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch, QuerySet

from apps.hebergements.models import HebergementModel
from apps.verifications import services as verifications
from apps.verifications.models import PieceIdentiteModel, VisiteModel


@dataclass(frozen=True)
class TypeMission:
    code: str
    libelle: str            # "Listings to visit"
    a_faire: Callable[[], QuerySet]
    champ_cle: str          # field that identifies the checked object (the target of the mission)
    resume: Callable[[object], dict]
    detail: Callable[[object], dict]


def nom(utilisateur) -> str:
    """First name and last name, or the email otherwise."""
    if utilisateur is None:
        return 'Un agent'
    return f"{utilisateur.first_name} {utilisateur.last_name}".strip() or utilisateur.email


def _piece_json(piece: PieceIdentiteModel | None) -> dict:
    from apps.verifications.views import _piece_json as piece_json  # same format as the host space

    return piece_json(piece)


# --- Listings to visit ------------------------------------------------------------------------------------------

def _logements():
    return (verifications.annonces_a_visiter().select_related('host', 'host__piece_identite')
            .prefetch_related(Prefetch('visites', queryset=VisiteModel.objects.only('id', 'decision', 'hebergement'))))


def _logement_resume(h: HebergementModel) -> dict:
    deja = any(v.decision == 'validee' for v in h.visites.all())
    return {
        'titre': h.name, 'sous_titre': f"{h.get_type_display()} · {nom(h.host)}", 'ville': h.city,
        'adresse': h.location, 'date': h.created_at, 'photo': h.image_url or next(iter(h.images or []), None),
        'etiquette': 'Modifiée après vérification' if deja else 'Nouvelle annonce',
    }


def _logement_detail(h: HebergementModel) -> dict:
    from apps.verifications.views import _visite_json

    return {
        'logement': _visite_json(h),
        'controles': VisiteModel.CONTROLES, 'max_photos': verifications.MAX_PHOTOS_VISITE,
    }


# --- Identity documents to check remotely ---------------------------------------------------------------------

def _pieces():
    return verifications.pieces_a_controler().select_related('hote').annotate(nb_annonces=Count('hote__hebergements'))


def _piece_resume(p: PieceIdentiteModel) -> dict:
    return {
        'titre': nom(p.hote), 'sous_titre': p.get_type_piece_display(), 'ville': '', 'adresse': '',
        'date': p.soumise_le, 'photo': None, 'etiquette': 'À distance',
    }


def _piece_detail(p: PieceIdentiteModel) -> dict:
    hote = p.hote
    return {
        'piece': {
            **_piece_json(p),
            'hote': {'id': str(hote.id), 'nom': nom(hote), 'email': hote.email, 'telephone': hote.phone,
                     'inscrit_le': hote.date_joined},
            'nb_annonces': getattr(p, 'nb_annonces', None),
        },
    }


TYPES: dict[str, TypeMission] = {
    'logement': TypeMission('logement', 'Logements à visiter', _logements, 'pk', _logement_resume, _logement_detail),
    'piece': TypeMission('piece', "Pièces d'identité", _pieces, 'hote_id', _piece_resume, _piece_detail),
}


def cle(type_mission: TypeMission, objet) -> str:
    return str(getattr(objet, type_mission.champ_cle))


def a_faire(type_mission: TypeMission, cible: str):
    """The object if it still waits for an agent, otherwise None (already checked, removed, or invalid id)."""
    try:
        return type_mission.a_faire().filter(**{type_mission.champ_cle: cible}).first()
    except (ValueError, ValidationError):  # malformed id (invalid UUID)
        return None
