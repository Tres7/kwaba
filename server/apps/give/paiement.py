"""Donations as a product paid online (registered in paiements at start-up)."""
from apps.paiements.api import ProduitPaye

from . import services
from .models import DonModel, ReversementModel


def _versements_periode(debut, fin) -> list[dict]:
    """Monthly transfers to the NGOs: done in the period, or still to do."""
    from django.db.models import Q

    qs = ReversementModel.objects.select_related('organisation').filter(
        Q(effectue_le__gte=debut.date(), effectue_le__lt=fin.date()) | ~Q(statut='effectue'))
    return [{
        'categorie': 'ONG (Kwa-Ba Give)', 'beneficiaire': r.organisation.nom, 'objet': f"Dons de {r.periode:%m/%Y}",
        'montant': r.montant, 'commission': 0, 'statut': 'envoye' if r.statut == 'effectue' else 'planifie',
        'date_prevue': r.date_prevue, 'envoye_le': r.effectue_le,
    } for r in qs if r.montant]


def _decrire_paiement(don_id) -> dict | None:
    d = DonModel.objects.filter(pk=don_id).select_related('organisation').first()
    if not d:
        return None
    return {'payeur': d.donateur, 'reference': d.reference, 'libelle': f"Don à {d.organisation.nom}", 'moyen': d.moyen}


PRODUIT_PAYE = ProduitPaye(type='don', decrire=_decrire_paiement, paiement_recu=services.paiement_recu,
                           passe=services.passe,
                           # Free for partner NGOs at launch: the payment fees paid by the donor are not a revenue
                           revenu=lambda ids: {}, versements_periode=_versements_periode)
