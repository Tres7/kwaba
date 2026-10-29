"""Donations as a product paid online (registered in paiements at start-up)."""
from apps.paiements.api import ProduitPaye

from . import services

PRODUIT_PAYE = ProduitPaye(type='don', paiement_recu=services.paiement_recu, passe=services.passe)
