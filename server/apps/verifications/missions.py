"""Field missions of the verifications: listings to visit and identity documents to check remotely."""
from django.db.models import Count, Prefetch

from apps.terrain.api import TypeMission, nom

from . import services as verifications
from .models import PieceIdentiteModel, VisiteModel
from .views import _piece_json, _visite_json


# --- Listings to visit ------------------------------------------------------------------------------------------

def _logements():
    return (verifications.annonces_a_visiter().select_related('host', 'host__piece_identite')
            .prefetch_related(Prefetch('visites', queryset=VisiteModel.objects.only('id', 'decision', 'hebergement'))))


def _logement_resume(h) -> dict:
    deja = any(v.decision == 'validee' for v in h.visites.all())
    return {
        'titre': h.name, 'sous_titre': f"{h.get_type_display()} · {nom(h.host)}", 'ville': h.city,
        'adresse': h.location, 'date': h.created_at, 'photo': h.image_url or next(iter(h.images or []), None),
        'etiquette': 'Modifiée après vérification' if deja else 'Nouvelle annonce',
    }


def _logement_detail(h) -> dict:
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


TYPES_MISSIONS = [
    TypeMission('logement', 'Logements à visiter', _logements, 'pk', _logement_resume, _logement_detail),
    TypeMission('piece', "Pièces d'identité", _pieces, 'hote_id', _piece_resume, _piece_detail),
]
