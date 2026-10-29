"""Car rentals as a product paid online (registered in paiements at start-up)."""
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import formats

from apps.paiements.api import ProduitPaye, Relance

from . import services
from .models import LocationModel, VersementPartenaireModel

FUSEAU = ZoneInfo('Africa/Lome')


def _decrire(loc) -> dict:
    return {'voyageur': loc.voyageur, 'montant': loc.prix, 'url': f"{settings.FRONTEND_URL}/location/{loc.id}",
            'quoi': f"votre location « {loc.libelle} », "
                    f"du {formats.date_format(loc.debut.astimezone(FUSEAU), 'j F')} "
                    f"au {formats.date_format(loc.fin.astimezone(FUSEAU), 'j F Y')}"}


PRODUIT_PAYE = ProduitPaye(
    type='location',
    paiement_recu=services.paiement_recu,
    passe=services.passe,
    versements=lambda payout_id: list(VersementPartenaireModel.objects.filter(payout_id=payout_id, statut='en_cours')),
    relance=Relance(
        requete=lambda: LocationModel.objects.select_related('voyageur', 'categorie'), champ_statut='statut',
        en_attente='en_attente_paiement', annule='annulee', champ_annule_par='annulee_par', decrire=_decrire,
    ),
)
