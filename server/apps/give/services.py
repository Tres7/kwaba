"""Life cycle of a Kwa-Ba Give donation.

    donation → "en_attente": the donor is sent to FedaPay or PayPal (one attempt = one donation)
        → payment received → "paye": receipt sent to the donor
        → payment refused, abandoned or not completed after 24 h → "echoue"
    every month, the worker groups the paid donations of the previous month into one transfer per NGO
        → the team transfers the funds, attaches the proof in the admin and sets the transfer to "effectue"
        → every donor concerned is notified; the proof is published on the NGO's page
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.paiements import services as paiements

from . import montants
from .models import DonModel, OrganisationModel, ReversementModel

logger = logging.getLogger('apps.give')

# Beyond that, a donation whose payment did not go through is classed as "not completed"
DELAI_ABANDON = timedelta(hours=24)


class DonErreur(Exception):
    """Error whose message can be shown as is to the donor."""


def organisations_publiees():
    return OrganisationModel.objects.filter(actif=True, verifiee_le__isnull=False)


def donner(*, donateur, organisation: OrganisationModel, projet=None, montant: int, couvre_frais: bool, moyen: str,
           partage_identite: bool = False) -> tuple[DonModel, str]:
    """Saves the donation and creates the transaction at the provider. Returns the donation and the payment address."""
    if not organisation.publiee:
        raise DonErreur("Cette organisation ne reçoit pas de dons pour le moment.")
    if projet and (projet.organisation_id != organisation.pk or not projet.actif):
        raise DonErreur("Ce projet ne reçoit pas de dons pour le moment.")
    if not montants.MONTANT_MIN <= montant <= montants.MONTANT_MAX:
        raise DonErreur(f"Le don doit être compris entre {montants.MONTANT_MIN} et {montants.MONTANT_MAX:,} FCFA."
                        .replace(',', ' '))
    if not paiements.paiement_actif():
        raise DonErreur("Les dons en ligne sont momentanément indisponibles.")

    calcul = montants.calculer(montant, couvre_frais)
    try:
        with transaction.atomic():
            don = DonModel.objects.create(
                donateur=donateur, organisation=organisation, projet=projet, montant=montant, couvre_frais=couvre_frais,
                frais=calcul.frais, total=calcul.total, montant_ong=calcul.montant_ong, moyen=moyen,
                partage_identite=partage_identite,
            )
            url = paiements.creer_paiement(
                objet=don, montant=don.total, moyen=moyen, voyageur=donateur,
                description=f"Don Kwa-Ba Give {don.reference}, {organisation.nom}",
                url_retour=f"{settings.FRONTEND_URL}/give/don/{don.id}",
            )
    except paiements.PaiementErreur as exc:
        raise DonErreur(str(exc)) from exc
    return don, url


def paiement_recu(paiement):
    """Called by apps.paiements, in its transaction, when the payment of a donation succeeds.
    A payment arriving after the "not completed" classification is accepted: the money was indeed given."""
    don = DonModel.objects.select_for_update().get(pk=paiement.don_id)
    if don.statut == 'paye':
        return
    don.statut, don.paye_le = 'paye', timezone.now()
    don.save(update_fields=['statut', 'paye_le'])
    logger.info("Don %s reçu : %s FCFA pour %s", don.reference, don.montant, don.organisation_id)


def synchroniser(don: DonModel) -> DonModel:
    """Reads the payment again at the provider (return page, worker) and updates the donation."""
    if don.statut != 'en_attente':
        return don
    paiement = don.paiements.order_by('-cree_le').first()
    if paiement:
        statut = paiements.synchroniser_paiement(paiement)
        if statut in ('echoue', 'annule'):
            DonModel.objects.filter(pk=don.pk, statut='en_attente').update(statut='echoue')
    don.refresh_from_db()
    return don


# --- Transfers to NGOs ----------------------------------------------------------------

def preparer_reversements(aujourd_hui=None) -> int:
    """Groups the paid donations of finished months into one transfer per NGO and per month. Returns the number of
    donations attached. A donation paid late (after the preparation) joins the transfer of its month if it is not
    done yet, otherwise the one of the following month."""
    aujourd_hui = aujourd_hui or timezone.localdate()
    debut_mois = montants.debut_du_mois(aujourd_hui)
    rattaches = 0
    a_reverser = (DonModel.objects.filter(statut='paye', reversement__isnull=True, paye_le__date__lt=debut_mois)
                  .order_by('paye_le'))
    for don in a_reverser:
        periode = montants.debut_du_mois(timezone.localtime(don.paye_le).date())
        with transaction.atomic():
            reversement = ReversementModel.objects.select_for_update().filter(
                organisation_id=don.organisation_id, periode=periode,
            ).first()
            if reversement and reversement.statut == 'effectue':
                # Month already transferred: the donation goes with the oldest transfer still being prepared
                periode = montants.mois_suivant(periode)
                reversement = ReversementModel.objects.select_for_update().filter(
                    organisation_id=don.organisation_id, periode=periode, statut='a_effectuer',
                ).first()
            if not reversement:
                reversement = ReversementModel.objects.create(
                    organisation_id=don.organisation_id, periode=periode, date_prevue=montants.date_reversement(periode),
                )
            DonModel.objects.filter(pk=don.pk).update(reversement=reversement)
            totaux = reversement.dons.aggregate(montant=Sum('montant_ong'), nb=Count('id'))
            reversement.montant, reversement.nb_dons = totaux['montant'] or 0, totaux['nb']
            reversement.save(update_fields=['montant', 'nb_dons'])
        rattaches += 1
    return rattaches


def marquer_effectue(reversement: ReversementModel, *, moyen: str, reference_operation: str, effectue_le=None):
    if reversement.statut == 'effectue':
        return
    reversement.statut, reversement.moyen = 'effectue', moyen
    reversement.reference_operation = reference_operation
    reversement.effectue_le = effectue_le or timezone.localdate()
    reversement.save(update_fields=['statut', 'moyen', 'reference_operation', 'effectue_le'])


# --- Impact ------------------------------------------------------------------------------

def impact(organisations=None) -> dict:
    """Amounts collected (owed to the NGOs), transferred and waiting to be transferred, in FCFA."""
    dons = DonModel.objects.filter(statut='paye')
    reversements = ReversementModel.objects.filter(statut='effectue')
    if organisations is not None:
        dons = dons.filter(organisation__in=organisations)
        reversements = reversements.filter(organisation__in=organisations)
    d = dons.aggregate(collecte=Sum('montant_ong'), nb=Count('id'), donateurs=Count('donateur', distinct=True))
    reverse = reversements.aggregate(total=Sum('montant'))['total'] or 0
    collecte = d['collecte'] or 0
    return {
        'collecte': collecte, 'reverse': reverse, 'en_attente': max(collecte - reverse, 0),
        'nb_dons': d['nb'], 'nb_donateurs': d['donateurs'],
    }


def impact_par_cause() -> dict:
    lignes = (DonModel.objects.filter(statut='paye').values('organisation__cause')
              .annotate(collecte=Sum('montant_ong'), nb=Count('id')))
    return {ligne['organisation__cause']: {'collecte': ligne['collecte'], 'nb_dons': ligne['nb']} for ligne in lignes}


# --- Worker ------------------------------------------------------------------------------

def abandonner() -> int:
    """Donations whose payment failed (recent payments are read again by the payments worker), then
    donations still pending after 24 h: last check at the provider and "not completed" classification."""
    abandonnes = DonModel.objects.filter(statut='en_attente', paiements__statut__in=('echoue', 'annule')).exclude(
        paiements__statut__in=('en_attente', 'reussi'),
    ).update(statut='echoue')
    for don in DonModel.objects.filter(statut='en_attente', cree_le__lt=timezone.now() - DELAI_ABANDON)[:50]:
        if synchroniser(don).statut == 'en_attente':
            abandonnes += DonModel.objects.filter(pk=don.pk, statut='en_attente').update(statut='echoue')
    return abandonnes


def passe() -> dict:
    from . import notifications  # local import: notifications imports the models

    return {
        'dons_non_aboutis': abandonner(),
        'dons_a_reverser': preparer_reversements(),
        'emails_give': notifications.envoyer_notifications(),
    }
