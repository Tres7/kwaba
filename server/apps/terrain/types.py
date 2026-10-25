"""Ce que contrôlent les agents de terrain, type par type.

Chaque type dit où trouver ce qui attend un agent (la file « à faire »), comment le résumer dans une liste et le
détailler dans sa fiche. Les décisions restent dans l'application du domaine (verifications pour les logements et
les pièces d'identité) : la mission n'en garde que l'issue.
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
    libelle: str            # « Logements à visiter »
    a_faire: Callable[[], QuerySet]
    champ_cle: str          # champ qui identifie l'objet contrôlé (la cible de la mission)
    resume: Callable[[object], dict]
    detail: Callable[[object], dict]


def nom(utilisateur) -> str:
    """Prénom et nom, ou l'email à défaut."""
    if utilisateur is None:
        return 'Un agent'
    return f"{utilisateur.first_name} {utilisateur.last_name}".strip() or utilisateur.email


def _piece_json(piece: PieceIdentiteModel | None) -> dict:
    from apps.verifications.views import _piece_json as piece_json  # même format que l'espace hôte

    return piece_json(piece)


# --- Logements à visiter ------------------------------------------------------------------------------------------

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


# --- Pièces d'identité à contrôler à distance ---------------------------------------------------------------------

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
    """L'objet s'il attend encore un agent, sinon None (déjà contrôlé, retiré, ou identifiant invalide)."""
    try:
        return type_mission.a_faire().filter(**{type_mission.champ_cle: cible}).first()
    except (ValueError, ValidationError):  # identifiant mal formé (UUID invalide)
        return None
