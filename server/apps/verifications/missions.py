"""Field missions of the verifications: listings to visit and identity documents to check remotely."""
from apps.terrain.api import TypeMission, nom

from . import services as verifications
from .models import PieceIdentiteModel, VisiteModel
from .views import _piece_json, pieces_avec_nb_annonces, visites_json


# --- Listings to visit ------------------------------------------------------------------------------------------

def _logements() -> list[dict]:
    return visites_json(verifications.annonces_a_visiter())


def _logement_resume(v: dict) -> dict:
    return {
        'titre': v['name'], 'sous_titre': f"{v['type_libelle']} · {v['hote']['nom'] or v['hote']['email']}",
        'ville': v['city'], 'adresse': v['location'], 'date': v['cree_le'],
        'photo': next(iter(v['photos']), None),
        'etiquette': 'Modifiée après vérification' if v['modifiee_apres_verification'] else 'Nouvelle annonce',
    }


def _logement_detail(v: dict) -> dict:
    return {
        'logement': v,
        'controles': VisiteModel.CONTROLES, 'max_photos': verifications.MAX_PHOTOS_VISITE,
    }


# --- Identity documents to check remotely ---------------------------------------------------------------------

def _pieces() -> list[PieceIdentiteModel]:
    return pieces_avec_nb_annonces(verifications.pieces_a_controler().select_related('hote'))


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


TYPES_MISSIONS = [
    TypeMission('logement', 'Logements à visiter', _logements, lambda v: v['id'], _logement_resume, _logement_detail),
    TypeMission('piece', "Pièces d'identité", _pieces, lambda p: p.hote_id, _piece_resume, _piece_detail),
]
