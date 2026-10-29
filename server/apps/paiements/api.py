from decimal import Decimal

from . import tarifs
from .documents import recu_paiement
from .models import ConditionsHoteModel, PaiementModel


def total_sejour(prix_par_nuit: Decimal, nuits: int) -> int:
    return tarifs.calculer(prix_par_nuit, nuits).total


def _paiement_reussi(type_objet: str, objet_id) -> PaiementModel | None:
    return (PaiementModel.objects.filter(**{f'{type_objet}_id': objet_id}, statut='reussi').order_by('cree_le').first())


def paiement_reussi(type_objet: str, objet_id) -> bool:
    """`type_objet`: reservation, transfert, location or don."""
    return _paiement_reussi(type_objet, objet_id) is not None


def recu_pdf(type_objet: str, objet_id) -> bytes | None:
    paiement = _paiement_reussi(type_objet, objet_id)
    return recu_paiement(paiement) if paiement else None


def texte_politique(reservation) -> str:
    return tarifs.texte_politique(reservation)


def frais_voyageur() -> Decimal:
    return tarifs.FRAIS_VOYAGEUR


def commission_hote() -> Decimal:
    return tarifs.COMMISSION_HOTE


def conditions_hote(hote_id) -> dict | None:
    """Category of the host (individual or hotel) and their Founders Programme dates, or None."""
    c = ConditionsHoteModel.objects.filter(hote_id=hote_id).first()
    if not c:
        return None
    return {'categorie': c.categorie, 'fondateur_debut': c.fondateur_debut, 'fondateur_fin': c.fondateur_fin}
