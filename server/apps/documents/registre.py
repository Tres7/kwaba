"""Products whose documents can be downloaded: each module registers its product at start-up (AppConfig.ready).

documents renders, numbers and serves the documents; the product module says how to find the object, who owns it,
whether it is paid, and builds its voucher and its receipt.
"""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Produit:
    type: str
    charger: Callable[[object], object]
    proprietaire_id: Callable[[object], object]
    reference: Callable[[object], str]
    paye: Callable[[object], bool]
    recu: Callable[[object], bytes]
    prefixe_recu: str = 'recu'
    bon: Callable[[object], bytes] | None = None
    facture: Callable[[object], dict] | None = None  # {'client_nom', 'client_email', 'lignes'}

    @property
    def documents(self) -> tuple[str, ...]:
        return tuple(d for d, present in (('bon', self.bon), ('recu', True), ('facture', self.facture)) if present)


PRODUITS: dict[str, Produit] = {}


def enregistrer(produit: Produit) -> None:
    PRODUITS[produit.type] = produit
