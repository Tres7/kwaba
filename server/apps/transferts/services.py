"""Life cycle of an airport transfer.

    transfer booking → "en_attente_paiement" (30 min to pay)
        → payment received → "confirme": the administrators are notified to assign a driver
        → driver assigned (admin) → "chauffeur_assigne": the traveller receives their contact details
          and the driver's payout is scheduled (arrival + 24 h)
        → the worker pays the driver and sets the transfer to "termine"
    cancellation by the traveller: full refund until 24 h before arrival, nothing afterwards
    cancellation by Kwa-Ba (no driver available…): full refund
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.paiements import api as paiements

from . import tarifs
from .models import AeroportModel, ChauffeurModel, TarifTransfertModel, TransfertModel, VersementChauffeurModel

logger = logging.getLogger('apps.transferts')


class TransfertErreur(Exception):
    """Error whose message can be shown as is to the traveller."""


def heure_locale(aeroport: AeroportModel, arrivee_naive: datetime) -> datetime:
    """Time typed by the traveller (local time of the airport) → timezone-aware datetime."""
    return arrivee_naive.replace(tzinfo=ZoneInfo(aeroport.fuseau))


def devis(aeroport: AeroportModel, arrivee: datetime, passagers: int, bagages: int) -> list[dict]:
    """Vehicle options with their price, for a given arrival (timezone-aware datetime)."""
    options = []
    for t in TarifTransfertModel.objects.filter(aeroport=aeroport, actif=True):
        cat = tarifs.CATEGORIES[t.categorie]
        prix = tarifs.calculer(t.prix)
        motif = tarifs.capacite_suffisante(t.categorie, passagers, bagages)
        options.append({
            'categorie': t.categorie, 'nom': cat['nom'], 'description': cat['description'],
            'passagers': cat['passagers'], 'bagages': cat['bagages'],
            'prix': prix.prix, 'disponible': motif is None, 'motif': motif or '',
        })
    return sorted(options, key=lambda o: o['prix'])


def creer(*, voyageur, aeroport: AeroportModel, arrivee: datetime, categorie: str, passagers: int, bagages: int,
          **champs) -> TransfertModel:
    if arrivee - timezone.now() < tarifs.DELAI_MIN_RESERVATION:
        heures = int(tarifs.DELAI_MIN_RESERVATION.total_seconds() // 3600)
        raise TransfertErreur(f"Réservez votre transfert au moins {heures} heures avant votre arrivée.")
    tarif = TarifTransfertModel.objects.filter(aeroport=aeroport, categorie=categorie, actif=True).first()
    if not tarif:
        raise TransfertErreur("Ce véhicule n'est pas proposé dans cet aéroport.")
    motif = tarifs.capacite_suffisante(categorie, passagers, bagages)
    if motif:
        raise TransfertErreur(f"Ce véhicule ne convient pas : {motif}.")

    if not paiements.reservation_possible():
        raise TransfertErreur(paiements.INDISPONIBLE)
    prix = tarifs.calculer(tarif.prix)
    en_ligne = paiements.paiement_actif()
    return TransfertModel.objects.create(
        voyageur=voyageur, aeroport=aeroport, arrivee=arrivee, categorie=categorie, passagers=passagers,
        bagages=bagages, prix=prix.prix, commission=prix.commission,
        statut='en_attente_paiement' if en_ligne else 'confirme',
        expire_le=timezone.now() + paiements.delai_paiement() if en_ligne else None,
        **champs,
    )


def demarrer_paiement(transfert: TransfertModel, moyen: str) -> str:
    if transfert.statut != 'en_attente_paiement':
        raise paiements.PaiementErreur("Ce transfert n'attend pas de paiement.")
    if transfert.expire_le and transfert.expire_le <= timezone.now():
        raise paiements.PaiementErreur("Le délai de paiement est dépassé. Refaites la réservation du transfert.")
    if transfert.moyen != moyen:
        transfert.moyen = moyen
        transfert.save(update_fields=['moyen'])
    return paiements.creer_paiement(
        objet=transfert, montant=transfert.prix, moyen=moyen, voyageur=transfert.voyageur,
        description=f"Kwa-Ba {transfert.reference}, transfert aéroport {transfert.aeroport.ville}",
        url_retour=f"{settings.FRONTEND_URL}/transfert/{transfert.id}",
    )


def paiement_recu(paiement):
    """Called by apps.paiements, in its transaction, when a transfer payment succeeds."""
    transfert = TransfertModel.objects.select_for_update().get(pk=paiement.transfert_id)
    if transfert.paiements.filter(statut='reussi').exclude(pk=paiement.pk).exists():
        paiements.rembourser(paiement, paiement.montant, "Paiement reçu en double")
        return
    if transfert.statut == 'annule' and transfert.annule_par != 'expiration':
        paiements.rembourser(paiement, paiement.montant, "Transfert annulé avant la confirmation du paiement")
        return
    transfert.statut, transfert.expire_le = 'confirme', None
    transfert.annule_par, transfert.annule_le = '', None
    transfert.save(update_fields=['statut', 'expire_le', 'annule_par', 'annule_le'])
    logger.info("Transfert %s payé : chauffeur à attribuer", transfert.reference)


def chauffeurs_disponibles(transfert: TransfertModel):
    """Active drivers of this airport, with a large enough vehicle."""
    rang = list(tarifs.CATEGORIES)
    adaptees = rang[rang.index(transfert.categorie):]
    return ChauffeurModel.objects.filter(actif=True, aeroports=transfert.aeroport, categorie__in=adaptees)


def assigner_chauffeur(transfert: TransfertModel, chauffeur: ChauffeurModel):
    """Assigns (or changes) the driver, and schedules their payout."""
    with transaction.atomic():
        transfert = TransfertModel.objects.select_for_update().get(pk=transfert.pk)
        if transfert.statut not in ('confirme', 'chauffeur_assigne'):
            raise TransfertErreur("Un chauffeur ne peut être attribué qu'à un transfert payé et non annulé.")
        changement = transfert.chauffeur_id not in (None, chauffeur.pk)
        transfert.chauffeur, transfert.statut = chauffeur, 'chauffeur_assigne'
        if changement:
            # The traveller receives the new driver's contact details, and the driver the ride details
            transfert.chauffeur_notifie = transfert.course_envoyee_chauffeur = False
        transfert.save(update_fields=['chauffeur', 'statut', 'chauffeur_notifie', 'course_envoyee_chauffeur'])
        VersementChauffeurModel.objects.update_or_create(
            transfert=transfert,
            defaults={
                'chauffeur': chauffeur, 'montant_brut': transfert.prix, 'commission': transfert.commission,
                'montant': transfert.montant_chauffeur, 'date_prevue': transfert.arrivee + tarifs.DELAI_VERSEMENT,
                'statut': 'planifie',
            },
        )
    logger.info("Chauffeur %s attribué au transfert %s", chauffeur.pk, transfert.reference)


def annuler(transfert: TransfertModel, par: str) -> int:
    """Cancels the transfer; returns the amount refunded to the traveller."""
    with transaction.atomic():
        transfert = TransfertModel.objects.select_for_update().get(pk=transfert.pk)
        if transfert.statut in ('annule', 'termine'):
            raise TransfertErreur("Ce transfert ne peut plus être annulé.")
        if par == 'voyageur' and transfert.arrivee <= timezone.now():
            raise TransfertErreur("L'heure d'arrivée est passée : ce transfert ne peut plus être annulé.")

        rembourse = 0
        paiement = transfert.paiements.filter(statut='reussi').order_by('cree_le').first()
        if paiement:
            gratuit = transfert.arrivee - timezone.now() > tarifs.DELAI_ANNULATION_GRATUITE
            if par != 'voyageur' or gratuit:
                rembourse = transfert.prix
                VersementChauffeurModel.objects.filter(transfert=transfert, statut__in=('planifie', 'echoue')).update(
                    statut='annule',
                )
            # Less than 24 h before arrival: the driver is already on the way, they are still paid
            motif = "Annulation par le voyageur" if par == 'voyageur' else "Annulation par Kwa-Ba"
            paiements.rembourser(paiement, rembourse, motif)

        transfert.statut, transfert.annule_par, transfert.annule_le = 'annule', par, timezone.now()
        transfert.save(update_fields=['statut', 'annule_par', 'annule_le'])
        return rembourse


# --- Worker ------------------------------------------------------------------------------

def expirer() -> int:
    expires = 0
    maintenant = timezone.now()
    for transfert in TransfertModel.objects.filter(statut='en_attente_paiement', expire_le__lte=maintenant):
        for paiement in transfert.paiements.filter(statut='en_attente'):
            paiements.synchroniser_paiement(paiement)
        expires += TransfertModel.objects.filter(pk=transfert.pk, statut='en_attente_paiement').update(
            statut='annule', annule_par='expiration', annule_le=maintenant,
        )
    return expires


def envoyer_versements_chauffeurs() -> int:
    if not paiements.fedapay_actif():
        return 0
    envoyes = 0
    dus = VersementChauffeurModel.objects.filter(
        statut='planifie', date_prevue__lte=timezone.now(), transfert__statut='chauffeur_assigne',
    ).select_related('chauffeur')[:50]
    for v in dus:
        c = v.chauffeur
        envoyes += paiements.envoyer_payout(
            v, mode=c.operateur_versement, numero=c.numero_versement, pays=c.pays_versement,
            email=c.email or settings.DEFAULT_FROM_EMAIL, titulaire=f"{c.prenom} {c.nom}",
        )
    for v in VersementChauffeurModel.objects.filter(statut='en_cours').exclude(payout_id='')[:50]:
        paiements.synchroniser_payout(v)
    # Driver paid: the ride is finished
    TransfertModel.objects.filter(statut='chauffeur_assigne', versement__statut='envoye').update(statut='termine')
    return envoyes


def passe() -> dict:
    from . import notifications  # local import: notifications imports the models

    return {
        'transferts_expires': expirer(),
        'versements_chauffeurs': envoyer_versements_chauffeurs(),
        'emails_transferts': notifications.envoyer_notifications(),
    }
