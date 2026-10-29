from decimal import Decimal

from . import notifications, tarifs
from .documents import recu_paiement
from .models import ConditionsHoteModel, PaiementModel
from .operateurs import OPERATEUR_CHOICES, PAYS_CHOICES
from .paypal import FCFA_PAR_EURO
from .services import (
    INDISPONIBLE, PaiementErreur, creer_paiement, delai_paiement, envoyer_payout, fedapay_actif,
    indiquer_numero_remboursement, moyens_actifs, paiement_actif, rembourser, reservation_possible,
    synchroniser_paiement, synchroniser_payout,
)
from .views import CompteRemboursementSerializer

__all__ = [
    'CompteRemboursementSerializer', 'FCFA_PAR_EURO', 'INDISPONIBLE', 'OPERATEUR_CHOICES', 'PAYS_CHOICES',
    'PaiementErreur', 'alerte_admin', 'date_fr', 'commission_hote', 'conditions_hote', 'creer_paiement', 'delai_paiement',
    'documents_joints', 'emails_admins', 'envoyer_email', 'envoyer_payout', 'fcfa', 'fedapay_actif', 'frais_voyageur',
    'indiquer_numero_remboursement', 'moyens_actifs', 'paiement_actif', 'paiement_reussi', 'recu_pdf', 'rembourser',
    'reservation_possible', 'synchroniser_paiement', 'synchroniser_payout', 'texte_politique', 'total_sejour',
    'frais_reduits', 'frais_reduits_sejour', 'hotes_deja_visites', 'rembourser_en_partie',
]

# Emails of the products paid online (stays, transfers, rentals, donations): same sending rules as the payment emails
envoyer_email = notifications._envoyer
emails_admins = notifications._admins
fcfa = notifications._fcfa
date_fr = notifications._date
documents_joints = notifications._documents
alerte_admin = notifications.alerte_admin


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


def frais_reduits_sejour(prix_nuits: int) -> int:
    """Service fees of a stay at the reduced rate (loyal customer, Stay Pack + Driver)."""
    return tarifs.arrondi(Decimal(prix_nuits) * tarifs.FRAIS_REDUITS)


def rembourser_en_partie(type_objet: str, objet_id, montant: int, motif: str) -> bool:
    """Refunds part of the successful payment of the object; False if it was never paid."""
    paiement = _paiement_reussi(type_objet, objet_id)
    if not paiement:
        return False
    rembourser(paiement, montant, motif)
    return True


def frais_reduits() -> Decimal:
    return tarifs.FRAIS_REDUITS


def hotes_deja_visites(voyageur) -> set:
    """Hosts the traveller already stayed with (loyal customer rate)."""
    return tarifs.hotes_deja_visites(voyageur)
