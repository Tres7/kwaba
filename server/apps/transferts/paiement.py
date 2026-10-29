"""Airport transfers as a product paid online (registered in paiements at start-up)."""
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import formats

from apps.paiements.api import ProduitPaye, Relance

from . import services
from .models import TransfertModel, VersementChauffeurModel

FUSEAU = ZoneInfo('Africa/Lome')


def _decrire(t) -> dict:
    return {'voyageur': t.voyageur, 'montant': t.prix, 'url': f"{settings.FRONTEND_URL}/transfert/{t.id}",
            'quoi': f"votre transfert depuis l'aéroport de {t.aeroport.ville} "
                    f"({formats.date_format(t.arrivee.astimezone(FUSEAU), 'j F Y')})"}


def _decrire_paiement(transfert_id) -> dict | None:
    t = TransfertModel.objects.filter(pk=transfert_id).select_related('aeroport').first()
    if not t:
        return None
    return {'payeur': t.voyageur, 'reference': t.reference, 'libelle': f"Transfert depuis l'aéroport {t.aeroport.ville}",
            'moyen': t.moyen}


PRODUIT_PAYE = ProduitPaye(
    type='transfert',
    decrire=_decrire_paiement,
    paiement_recu=services.paiement_recu,
    passe=services.passe,
    versements=lambda payout_id: list(VersementChauffeurModel.objects.filter(payout_id=payout_id, statut='en_cours')),
    relance=Relance(
        requete=lambda: TransfertModel.objects.select_related('aeroport'), champ_statut='statut',
        en_attente='en_attente_paiement', annule='annule', champ_annule_par='annule_par', decrire=_decrire,
    ),
)
