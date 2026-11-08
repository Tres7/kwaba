"""Sending a wizard draft for verification: what must be done first, decided here and never by the browser."""
import re
import uuid
from collections.abc import Iterable

from apps.contrats import api as contrats
from apps.paiements import api as paiements
from apps.verifications import api as verifications

from .models import HebergementPhotoModel

MIN_PHOTOS = 5
# hebergements/<host>/<photo id>.jpg (see models._photo_upload_path)
_PHOTO = re.compile(r'/hebergements/[^/]+/([0-9a-f-]{36})\.jpg')


def ids_photos(urls: Iterable[str]) -> list[uuid.UUID] | None:
    """Ids of the uploaded photos behind these addresses, or None if one of them is not an uploaded photo."""
    ids = []
    for url in urls:
        trouve = _PHOTO.search(url)
        if not trouve:
            return None
        try:
            ids.append(uuid.UUID(trouve[1]))
        except ValueError:
            return None
    return ids


def photos_du_compte(hote_id: uuid.UUID, urls: list[str]) -> bool:
    """Every photo was uploaded by this host: never someone else's, nor an image from elsewhere."""
    ids = ids_photos(urls)
    return ids is not None and HebergementPhotoModel.objects.filter(owner_id=hote_id, pk__in=ids).count() == len(set(ids))


def conditions(hote, donnees: dict) -> dict:
    """State of what the host must have done, for the wizard's screens and the recap."""
    images = donnees.get('images') or []
    return {
        'photos': len(images) >= MIN_PHOTOS,
        'photos_du_compte': photos_du_compte(hote.pk, images),
        'attestation': (donnees.get('declarations') or {}).get('attestation') is True,
        'telephone': bool(hote.phone),
        'identite': verifications.statut_piece(hote),
        'versement': paiements.a_profil_versement(hote.pk),
        'preinscription': not contrats.preinscription_requise(hote),
        # Never blocks the sending: without a signature, the agents simply do not visit yet
        'contrat_a_signer': verifications.contrat_manquant(hote),
    }


def bloquants(etat: dict) -> list[str]:
    """What prevents sending the listing, among the conditions."""
    manquants = [cle for cle in ('photos', 'photos_du_compte', 'attestation', 'telephone', 'versement', 'preinscription')
                 if not etat[cle]]
    if etat['identite'] not in ('soumise', 'verifiee'):
        manquants.append('identite')
    return manquants
