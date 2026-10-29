"""Donations as a product paid online (registered in paiements at start-up)."""
from apps.paiements.api import ProduitPaye

from . import services
from .models import DonModel


def _decrire_paiement(don_id) -> dict | None:
    d = DonModel.objects.filter(pk=don_id).select_related('organisation').first()
    if not d:
        return None
    return {'payeur': d.donateur, 'reference': d.reference, 'libelle': f"Don à {d.organisation.nom}", 'moyen': d.moyen}


PRODUIT_PAYE = ProduitPaye(type='don', decrire=_decrire_paiement, paiement_recu=services.paiement_recu,
                           passe=services.passe)
