"""Stays as a product paid online (registered in paiements at start-up)."""
from django.conf import settings
from django.utils import formats

from apps.hebergements import api as hebergements
from apps.paiements.api import ProduitPaye, Relance

from .models import ReservationModel


def _decrire(r) -> dict:
    annonce = hebergements.fiche(r.hebergement_id, archivees=True)
    return {'voyageur': r.guest, 'montant': int(r.total_price),
            'url': f"{settings.FRONTEND_URL}/reservation/paiement/{r.id}",
            'quoi': f"votre séjour « {annonce['name']} » ({annonce['city']}), "
                    f"du {formats.date_format(r.check_in, 'j F')} au {formats.date_format(r.check_out, 'j F Y')}"}


PRODUIT_PAYE = ProduitPaye(
    type='reservation',
    relance=Relance(
        requete=lambda: ReservationModel.objects.select_related('guest'), champ_statut='status', en_attente='pending',
        annule='cancelled', champ_annule_par='annule_par', decrire=_decrire,
    ),
)
