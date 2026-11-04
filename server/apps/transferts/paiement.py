"""Airport transfers as a product paid online (registered in paiements at start-up)."""
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import formats

from django.db.models import Q

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


def _a_regarder(qs, debut, fin):
    """Payouts sent in [debut, fin), or not sent yet (due)."""
    return qs.filter(Q(envoye_le__gte=debut, envoye_le__lt=fin) | Q(statut__in=('planifie', 'en_cours', 'echoue')))


def _versements_periode(debut, fin) -> list[dict]:
    return [{
        'categorie': 'Chauffeur (transfert)', 'beneficiaire': str(v.chauffeur), 'objet': v.transfert.reference,
        'montant': v.montant, 'commission': v.commission, 'statut': v.statut, 'date_prevue': v.date_prevue,
        'envoye_le': v.envoye_le,
    } for v in _a_regarder(VersementChauffeurModel.objects.select_related('chauffeur', 'transfert'), debut, fin)]


PRODUIT_PAYE = ProduitPaye(
    type='transfert',
    revenu=lambda ids: dict(TransfertModel.objects.filter(pk__in=list(ids)).values_list('pk', 'commission')),
    versements_periode=_versements_periode,
    decrire=_decrire_paiement,
    paiement_recu=services.paiement_recu,
    passe=services.passe,
    versements=lambda payout_id: list(VersementChauffeurModel.objects.filter(payout_id=payout_id, statut='en_cours')),
    relance=Relance(
        requete=lambda: TransfertModel.objects.select_related('aeroport'), champ_statut='statut',
        en_attente='en_attente_paiement', annule='annule', champ_annule_par='annule_par', decrire=_decrire,
    ),
)
