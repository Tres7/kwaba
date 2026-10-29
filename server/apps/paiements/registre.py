"""Products paid online (stays, transfers, rentals, donations): each module registers its product at start-up
(AppConfig.ready), so that paiements never imports them.
"""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Relance:
    """Payment reminders of a product: objects waiting for a payment, and how the emails describe them."""
    requete: Callable[[], object]       # queryset of the objects (with their traveller)
    champ_statut: str
    en_attente: str
    annule: str
    champ_annule_par: str
    decrire: Callable[[object], dict]   # {'voyageur', 'quoi', 'montant', 'url'}


@dataclass(frozen=True)
class ProduitPaye:
    type: str                                                # reservation, transfert, location or don
    # object id -> {'payeur': user, 'reference', 'libelle', 'moyen'} (receipts, refunds, emails); None if unknown
    decrire: Callable[[object], dict | None] = None
    paiement_recu: Callable[[object], None] | None = None    # in the payment's transaction, once it succeeded
    passe: Callable[[], dict] | None = None                  # the product's part of the worker's pass
    versements: Callable[[str], list] | None = None          # payout id -> its ongoing payout lines (webhook)
    relance: Relance | None = None


PRODUITS: dict[str, ProduitPaye] = {}


def enregistrer(produit: ProduitPaye) -> None:
    PRODUITS[produit.type] = produit
