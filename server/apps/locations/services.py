"""Life cycle of a car rental (or of a driver for the customer's vehicle).

    request (vehicle, option, places, dates, details) at least `delai_min_jours` before the pick-up
        → "en_attente_paiement" (same payment period as stays)
        → payment received → "confirmee": administrators are notified to assign
        → owner and/or driver assigned (admin) → "partenaire_assigne": the traveller receives their
          contact details, they receive the details, and their payouts are scheduled
        → the worker pays the owner and the driver, then sets the rental to "terminee"
    cancellation by the traveller (terms of sale, appendix 1): full refund until `annulation_gratuite_heures` (48 h)
    before the pick-up, 50 % until 24 h before, nothing afterwards; 48 h cooling-off period at least 7 days before
    (terms of sale, art. 10.3)
    cancellation by Kwa-Ba (no owner or driver available…): full refund

Prices (terms of sale, art. 6.5): vehicle price set by the owner (no service fees for the customer); driver
7,000 FCFA per day, of which 6,000 for them (6,500 with the Excellence status or if asked for again: "My driver");
travel allowances (1,500 FCFA per day outside Lomé, 2,000 outside the country) fully paid to the driver. Owner's
commission: 15 %, 10 % during the Founders Programme, 12 % after 20 rentals without incident.

Deposit (car only): paid online with the rental and kept by Kwa-Ba, the traveller pays nothing to the
owner; halved after 3 rentals without incident. After the return, the owner has `restitution_caution_heures`
to report damage to Kwa-Ba, which records a withheld amount (back-office); the deposit minus the withheld
amount is then refunded to the traveller, the withheld amount paid to the owner. A cancelled rental always
gives the deposit back.
"""
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.paiements import services as paiements
from config.site import module_actif

from .models import (
    CategorieVehiculeModel, LieuRemiseModel, LocationModel, ParametresLocationModel, PartenaireLocationModel,
    VersementChauffeurLocationModel, VersementPartenaireModel,
)

logger = logging.getLogger('apps.locations')

DELAI_VERSEMENT = timedelta(hours=24)

# Driver (mobility offer, terms of sale art. 6.5, driver contract art. 3)
CHAUFFEUR_JOUR = 7000
PART_KWABA_JOUR = 1000
PART_KWABA_JOUR_REDUITE = 500  # Excellence driver or "My driver": the driver gets 6,500
PRIME_HORS_LOME = 1500
PRIME_HORS_PAYS = 2000
# Owner's commission
COMMISSION_FONDATEUR = Decimal('10')
COMMISSION_FIDELE = Decimal('12')
LOCATIONS_FIDELE = 20
# Deposit halved for a customer who has made 3 rentals without incident
LOCATIONS_CLIENT_FIDELE = 3
# Cancellation (terms of sale, appendix 1) and cooling-off period (art. 10.3)
DEMI_REMBOURSEMENT = timedelta(hours=24)
REFLEXION, REFLEXION_AVANT = timedelta(hours=48), timedelta(days=7)


class LocationErreur(Exception):
    """Error whose message can be shown as is to the traveller."""


def _arrondi(montant) -> int:
    return int(Decimal(montant).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def categories_proposees():
    """Active vehicles, with a price, whose insurance and roadworthiness test have not expired."""
    aujourd_hui = timezone.localdate()
    return (CategorieVehiculeModel.objects.filter(actif=True, prix_jour__isnull=False)
            .filter(Q(sans_chauffeur=True) | Q(avec_chauffeur=True))
            .exclude(assurance_fin__lt=aujourd_hui).exclude(visite_technique_fin__lt=aujourd_hui)
            .exclude(proprietaire__actif=False)
            .prefetch_related('photos'))


def active() -> bool:
    """Rental is offered only if the administration has fully set it up."""
    return (ParametresLocationModel.courants() is not None and categories_proposees().exists()
            and LieuRemiseModel.objects.filter(actif=True).exists())


def heure_locale(lieu: LieuRemiseModel, naive: datetime) -> datetime:
    """Time typed by the traveller (local time of the handover place) → timezone-aware datetime."""
    return naive.replace(tzinfo=ZoneInfo(lieu.fuseau))


def nombre_de_jours(debut: datetime, fin: datetime) -> int:
    """Per started 24 h period (pick-up at 10 am, return the next day at 12 pm: 2 days)."""
    return max(1, math.ceil((fin - debut) / timedelta(hours=24)))


# --- Taux -------------------------------------------------------------------------------------------

def taux_commission(params: ParametresLocationModel, partenaire: PartenaireLocationModel | None, jour=None) -> Decimal:
    """Owner's commission in %: 15 (settings), 10 during the Founders Programme, 12 with the Loyal status."""
    taux = Decimal(params.commission_pourcent)
    if partenaire is None:
        return taux
    jour = jour or timezone.localdate()
    if partenaire.fondateur_debut and partenaire.fondateur_fin and partenaire.fondateur_debut <= jour <= partenaire.fondateur_fin:
        taux = min(taux, COMMISSION_FONDATEUR)
    if partenaire.locations.filter(statut='terminee', caution_retenue=0).count() >= LOCATIONS_FIDELE:
        taux = min(taux, COMMISSION_FIDELE)
    return taux


def client_sans_incident(voyageur) -> bool:
    """At least 3 finished rentals without any amount withheld from the deposit: deposit halved."""
    if not voyageur or not getattr(voyageur, 'is_authenticated', False):
        return False
    return LocationModel.objects.filter(voyageur=voyageur, statut='terminee', caution_retenue=0).count() >= LOCATIONS_CLIENT_FIDELE


def mes_chauffeurs(voyageur):
    """Drivers who have already driven this traveller (finished rental or transfer): "My driver"."""
    from apps.transferts.models import ChauffeurModel

    return ChauffeurModel.objects.filter(actif=True).filter(
        Q(locations__voyageur=voyageur, locations__statut='terminee')
        | Q(transferts__voyageur=voyageur, transferts__statut='termine'),
    ).distinct()


# --- Prix -------------------------------------------------------------------------------------------

@dataclass
class Devis:
    jours: int
    prix_jour: int
    frais_lieux: int
    prix_chauffeur: int
    primes: int
    prix: int
    commission: int
    part_kwaba_chauffeur: int
    caution: int


def chiffrer(params: ParametresLocationModel, categorie: CategorieVehiculeModel | None, formule: str,
             lieu_prise: LieuRemiseModel, lieu_retour: LieuRemiseModel, debut: datetime, fin: datetime,
             voyageur=None, jours_hors_lome: int = 0, jours_hors_pays: int = 0) -> Devis:
    jours = nombre_de_jours(debut, fin)
    if formule not in dict(LocationModel.FORMULES):
        raise LocationErreur("Formule inconnue.")
    if formule == 'sans_chauffeur' and not module_actif('location_sans_chauffeur'):
        # Hors de l'offre de lancement (interrupteur MODULE_LOCATION_SANS_CHAUFFEUR)
        raise LocationErreur("La location sans chauffeur n'est pas encore proposée.")
    avec_chauffeur = formule in ('avec_chauffeur', 'chauffeur_seul')
    if formule == 'chauffeur_seul':
        prix_jour, frais, caution, commission = 0, 0, 0, 0
    else:
        if categorie is None or not categorie.propose(formule):
            raise LocationErreur("Cette formule n'est pas proposée pour ce véhicule.")
        prix_jour = categorie.prix_jour
        frais = lieu_prise.frais + lieu_retour.frais
        taux = taux_commission(params, categorie.proprietaire)
        commission = _arrondi(Decimal(prix_jour * jours) * taux / 100)
        caution = categorie.caution if formule == 'sans_chauffeur' else 0
        if caution and client_sans_incident(voyageur):
            caution = _arrondi(Decimal(caution) / 2)
    if not avec_chauffeur:
        jours_hors_lome = jours_hors_pays = 0
    if jours_hors_lome < 0 or jours_hors_pays < 0 or jours_hors_lome + jours_hors_pays > jours:
        raise LocationErreur(f"Les jours hors de Lomé ne peuvent pas dépasser la durée de la location ({jours} jours).")
    prix_chauffeur = CHAUFFEUR_JOUR * jours if avec_chauffeur else 0
    primes = PRIME_HORS_LOME * jours_hors_lome + PRIME_HORS_PAYS * jours_hors_pays
    return Devis(
        jours=jours, prix_jour=prix_jour, frais_lieux=frais, prix_chauffeur=prix_chauffeur, primes=primes,
        prix=prix_jour * jours + frais + prix_chauffeur + primes, commission=commission,
        part_kwaba_chauffeur=PART_KWABA_JOUR * jours if avec_chauffeur else 0, caution=caution,
    )


def verifier_dates(params: ParametresLocationModel, debut: datetime, fin: datetime) -> None:
    if fin <= debut:
        raise LocationErreur("Le retour doit être après la prise du véhicule.")
    if debut - timezone.now() < timedelta(days=params.delai_min_jours):
        raise LocationErreur(
            f"Réservez au moins {params.delai_min_jours} jours avant : "
            "le propriétaire et le chauffeur ont besoin de ce délai pour se préparer."
        )
    if nombre_de_jours(debut, fin) > params.duree_max_jours:
        raise LocationErreur(f"La location est limitée à {params.duree_max_jours} jours.")


def creer(*, voyageur, categorie: CategorieVehiculeModel | None, formule: str, lieu_prise: LieuRemiseModel,
          lieu_retour: LieuRemiseModel, debut: datetime, fin: datetime, passagers: int, jours_hors_lome: int = 0,
          jours_hors_pays: int = 0, chauffeur_demande=None, **champs) -> LocationModel:
    params = ParametresLocationModel.courants()
    if not params or not active():
        raise LocationErreur("La location de voitures n'est pas encore disponible.")
    if formule == 'chauffeur_seul':
        categorie = None
    else:
        if categorie is None or not categories_proposees().filter(pk=categorie.pk).exists():
            raise LocationErreur("Ce véhicule n'est plus proposé.")
        if passagers > categorie.places:
            raise LocationErreur(f"Ce véhicule accueille {categorie.places} personnes au plus.")
    if not (lieu_prise.actif and lieu_retour.actif):
        raise LocationErreur("Ce lieu de remise n'est plus proposé.")
    for lieu, cle in ((lieu_prise, 'adresse_prise'), (lieu_retour, 'adresse_retour')):
        if lieu.adresse_requise and len(champs.get(cle, '').strip()) < 5:
            raise LocationErreur(f"Indiquez l'adresse pour « {lieu.nom} ».")
    if formule == 'sans_chauffeur' and not all(champs.get(c, '').strip() for c in ('conducteur', 'permis_numero', 'permis_pays')):
        raise LocationErreur("Pour conduire vous-même, indiquez le nom du conducteur et son permis de conduire.")
    if chauffeur_demande and (formule == 'sans_chauffeur' or not mes_chauffeurs(voyageur).filter(pk=chauffeur_demande.pk).exists()):
        raise LocationErreur("Vous ne pouvez redemander qu'un chauffeur qui vous a déjà conduit.")
    verifier_dates(params, debut, fin)

    if not paiements.reservation_possible():
        raise LocationErreur(paiements.INDISPONIBLE)
    devis = chiffrer(params, categorie, formule, lieu_prise, lieu_retour, debut, fin, voyageur=voyageur,
                     jours_hors_lome=jours_hors_lome, jours_hors_pays=jours_hors_pays)
    en_ligne = paiements.paiement_actif()
    return LocationModel.objects.create(
        voyageur=voyageur, categorie=categorie, formule=formule, lieu_prise=lieu_prise, lieu_retour=lieu_retour,
        debut=debut, fin=fin, passagers=passagers, jours=devis.jours, prix_jour=devis.prix_jour,
        frais_lieux=devis.frais_lieux, prix_chauffeur=devis.prix_chauffeur, primes=devis.primes, prix=devis.prix,
        commission=devis.commission, part_kwaba_chauffeur=devis.part_kwaba_chauffeur, caution=devis.caution,
        caution_en_ligne=params.caution_en_ligne and devis.caution > 0,
        jours_hors_lome=jours_hors_lome if devis.prix_chauffeur else 0,
        jours_hors_pays=jours_hors_pays if devis.prix_chauffeur else 0, chauffeur_demande=chauffeur_demande,
        statut='en_attente_paiement' if en_ligne else 'confirmee',
        expire_le=timezone.now() + paiements.delai_paiement() if en_ligne else None,
        **champs,
    )


def demarrer_paiement(location: LocationModel, moyen: str) -> str:
    if location.statut != 'en_attente_paiement':
        raise paiements.PaiementErreur("Cette location n'attend pas de paiement.")
    if location.expire_le and location.expire_le <= timezone.now():
        raise paiements.PaiementErreur("Le délai de paiement est dépassé. Refaites la demande de location.")
    if location.moyen != moyen:
        location.moyen = moyen
        location.save(update_fields=['moyen'])
    return paiements.creer_paiement(
        objet=location, montant=location.montant_a_payer, moyen=moyen, voyageur=location.voyageur,
        description=f"Kwa-Ba {location.reference}, {location.libelle}, {location.lieu_prise.ville}",
        url_retour=f"{settings.FRONTEND_URL}/location/{location.id}",
    )


def appliquer_pack_sejour(location: LocationModel) -> int:
    """Stay Pack + Driver (terms of sale, art. 6.4): an upcoming Kwa-Ba stay booked with an option with a driver gets
    service fees lowered to 3 %; the difference is refunded to the traveller. Returns the refunded amount."""
    from apps.paiements import tarifs
    from apps.reservations.models import ReservationModel

    if not location.reservation_id or not location.avec_chauffeur:
        return 0
    r = ReservationModel.objects.select_for_update().filter(pk=location.reservation_id).first()
    if not r or r.guest_id != location.voyageur_id or r.status != 'confirmed' or r.check_in <= timezone.localdate():
        return 0
    if r.prix_nuits is None or r.frais_service is None:
        return 0
    nouveaux_frais = tarifs.arrondi(Decimal(r.prix_nuits) * tarifs.FRAIS_REDUITS)
    ecart = r.frais_service - nouveaux_frais
    if ecart <= 0:
        return 0
    r.frais_service, r.total_price = nouveaux_frais, r.prix_nuits + nouveaux_frais
    r.save(update_fields=['frais_service', 'total_price'])
    paiement = paiements.paiement_reussi(r)
    if paiement:
        paiements.rembourser(paiement, ecart, "Pack Séjour + Chauffeur : frais de service ramenés à 3 %")
    logger.info("Pack Séjour : %s FCFA rendus sur %s (location %s)", ecart, r.reference, location.reference)
    return ecart


def paiement_recu(paiement):
    """Called by apps.paiements, in its transaction, when a rental payment succeeds."""
    location = LocationModel.objects.select_for_update().get(pk=paiement.location_id)
    if location.paiements.filter(statut='reussi').exclude(pk=paiement.pk).exists():
        paiements.rembourser(paiement, paiement.montant, "Paiement reçu en double")
        return
    if location.statut == 'annulee' and location.annulee_par != 'expiration':
        paiements.rembourser(paiement, paiement.montant, "Location annulée avant la confirmation du paiement")
        return
    location.statut, location.expire_le = 'confirmee', None
    location.annulee_par, location.annulee_le = '', None
    location.save(update_fields=['statut', 'expire_le', 'annulee_par', 'annulee_le'])
    appliquer_pack_sejour(location)
    logger.info("Location %s payée : à attribuer", location.reference)


# --- Attribution ------------------------------------------------------------------------------------

def partenaires_disponibles(location: LocationModel):
    """Owner of the vehicle; for old categories without an owner, the rental companies offering it at this
    handover place. None for a driver alone."""
    if location.categorie_id is None:
        return PartenaireLocationModel.objects.none()
    if location.categorie.proprietaire_id:
        return PartenaireLocationModel.objects.filter(pk=location.categorie.proprietaire_id, actif=True)
    return PartenaireLocationModel.objects.filter(
        actif=True, categories=location.categorie, lieux=location.lieu_prise,
    ).distinct()


def chauffeurs_disponibles(location: LocationModel):
    """Active partner drivers, the driver asked for again ("My driver") and the Excellence ones first."""
    from django.db.models import Case, IntegerField, Value, When

    from apps.transferts.models import ChauffeurModel

    return ChauffeurModel.objects.filter(actif=True).annotate(
        demande=Case(When(pk=location.chauffeur_demande_id, then=Value(0)), default=Value(1), output_field=IntegerField()),
    ).order_by('demande', '-excellence', 'prenom')


def _date_versement(location: LocationModel):
    """Owner: 24 h after the start of the rental; with an online deposit, after the return and the end of the
    damage reporting period, to pay any withheld amount with the rental."""
    if location.caution_gardee:
        params = ParametresLocationModel.courants()
        return location.fin + max(DELAI_VERSEMENT, timedelta(hours=params.restitution_caution_heures if params else 24))
    return location.debut + DELAI_VERSEMENT


def _montants_versement(location: LocationModel, part: Decimal = Decimal(1)) -> dict:
    """Owner: vehicle and handover fees (and amount withheld from the deposit), minus the commission. `part`: fraction
    kept after a late cancellation."""
    brut = _arrondi(location.part_proprietaire * part) + location.caution_retenue
    commission = _arrondi(location.commission * part)
    return {'montant_brut': brut, 'commission': commission, 'montant': brut - commission}


def _montants_chauffeur(location: LocationModel, part: Decimal = Decimal(1)) -> dict:
    brut = _arrondi((location.prix_chauffeur + location.primes) * part)
    commission = _arrondi(location.part_kwaba_chauffeur * part)
    return {'montant_brut': brut, 'commission': commission, 'montant': brut - commission}


def attribuer(location: LocationModel, *, partenaire: PartenaireLocationModel | None = None, chauffeur=None,
              vehicule: str = '', immatriculation: str = ''):
    """Assigns (or changes) the owner and/or the partner driver, records the handed-over vehicle, schedules the
    payouts. The driver gets 6,500 FCFA per day with the Excellence status or if they were asked for again."""
    with transaction.atomic():
        location = LocationModel.objects.select_for_update(of=('self',)).select_related('categorie').get(pk=location.pk)
        if location.statut not in ('confirmee', 'partenaire_assigne'):
            raise LocationErreur("Une location ne peut être attribuée que payée et non annulée.")
        if location.formule != 'chauffeur_seul' and not partenaire:
            raise LocationErreur("Choisissez le propriétaire du véhicule.")
        if location.formule == 'chauffeur_seul':
            partenaire = None
        if location.avec_chauffeur and not chauffeur:
            raise LocationErreur("Formule avec chauffeur : choisissez le chauffeur partenaire.")
        if not location.avec_chauffeur:
            chauffeur = None
        if partenaire and not partenaires_disponibles(location).filter(pk=partenaire.pk).exists():
            raise LocationErreur("Ce propriétaire ne fournit pas ce véhicule à ce lieu de remise.")

        changement = ((location.partenaire_id and location.partenaire_id != getattr(partenaire, 'pk', None))
                      or (location.chauffeur_partenaire_id and location.chauffeur_partenaire_id != getattr(chauffeur, 'pk', None)))
        location.partenaire, location.chauffeur_partenaire, location.statut = partenaire, chauffeur, 'partenaire_assigne'
        categorie = location.categorie
        location.vehicule = vehicule or (f"{categorie.exemple_modele or categorie.nom}" if categorie else '')
        location.immatriculation = immatriculation or (categorie.immatriculation if categorie else '')
        if chauffeur:
            location.chauffeur_nom, location.chauffeur_telephone = f"{chauffeur.prenom} {chauffeur.nom}", chauffeur.telephone
            reduite = chauffeur.excellence or chauffeur.pk == location.chauffeur_demande_id
            location.part_kwaba_chauffeur = (PART_KWABA_JOUR_REDUITE if reduite else PART_KWABA_JOUR) * location.jours
        else:
            location.chauffeur_nom = location.chauffeur_telephone = ''
        if changement:
            # The traveller receives the new contact details, and the new partners the details
            location.partenaire_notifie = location.location_envoyee_partenaire = location.mission_envoyee_chauffeur = False
        location.save()

        if partenaire:
            VersementPartenaireModel.objects.update_or_create(location=location, defaults={
                'partenaire': partenaire, **_montants_versement(location), 'date_prevue': _date_versement(location),
                'statut': 'planifie',
            })
        else:
            VersementPartenaireModel.objects.filter(location=location, statut__in=('planifie', 'echoue')).update(statut='annule')
        if chauffeur:
            VersementChauffeurLocationModel.objects.update_or_create(location=location, defaults={
                'chauffeur': chauffeur, **_montants_chauffeur(location), 'date_prevue': location.fin + DELAI_VERSEMENT,
                'statut': 'planifie',
            })
        else:
            VersementChauffeurLocationModel.objects.filter(location=location, statut__in=('planifie', 'echoue')).update(statut='annule')
    logger.info("Location %s attribuée (propriétaire %s, chauffeur %s)", location.reference,
                getattr(partenaire, 'pk', None), getattr(chauffeur, 'pk', None))
    return location


# --- Annulation ----------------------------------------------------------------------------------

def retenue_si_annulation(location: LocationModel, maintenant=None) -> int:
    """Share of the price kept if the traveller cancels now (terms of sale, appendix 1 and art. 10.3)."""
    maintenant = maintenant or timezone.now()
    delai = location.debut - maintenant
    if maintenant - location.cree_le <= REFLEXION and delai >= REFLEXION_AVANT:
        return 0
    params = ParametresLocationModel.courants()
    if delai >= timedelta(hours=params.annulation_gratuite_heures if params else 48):
        return 0
    if delai >= DEMI_REMBOURSEMENT:
        return _arrondi(Decimal(location.prix) / 2)
    return location.prix


def annulation_gratuite(location: LocationModel) -> bool:
    return retenue_si_annulation(location) == 0


def annuler(location: LocationModel, par: str) -> int:
    """Cancels the rental; returns the amount refunded to the traveller. For a late cancellation, the kept share is
    paid to the owner and the driver, pro rata."""
    with transaction.atomic():
        location = LocationModel.objects.select_for_update().get(pk=location.pk)
        if location.statut in ('annulee', 'terminee'):
            raise LocationErreur("Cette location ne peut plus être annulée.")
        if par == 'voyageur' and location.debut <= timezone.now():
            raise LocationErreur("La location a commencé : elle ne peut plus être annulée.")

        rembourse = 0
        paiement = location.paiements.filter(statut='reussi').order_by('cree_le').first()
        if paiement:
            retenu = retenue_si_annulation(location) if par == 'voyageur' else 0
            rembourse = location.prix - retenu
            part = Decimal(retenu) / location.prix if location.prix else Decimal(0)
            for modele, montants in ((VersementPartenaireModel, _montants_versement), (VersementChauffeurLocationModel, _montants_chauffeur)):
                for v in modele.objects.select_for_update().filter(location=location, statut__in=('planifie', 'echoue')):
                    if part:
                        for champ, valeur in montants(location, part).items():
                            setattr(v, champ, valeur)
                        v.statut = 'planifie'
                    else:
                        v.statut = 'annule'
                    v.save()
            # The deposit is always given back: the vehicle was not handed over
            if location.caution_gardee and not location.caution_restituee_le:
                rembourse += location.caution_gardee
                location.caution_retenue, location.caution_restituee_le = 0, timezone.now()
            motif = "Annulation par le voyageur" if par == 'voyageur' else "Annulation par Kwa-Ba"
            paiements.rembourser(paiement, rembourse, motif)

        location.statut, location.annulee_par, location.annulee_le = 'annulee', par, timezone.now()
        location.save(update_fields=['statut', 'annulee_par', 'annulee_le', 'caution_retenue', 'caution_restituee_le'])
        return rembourse


def retenir_caution(location: LocationModel, montant: int, motif: str) -> LocationModel:
    """Amount withheld from the deposit (damage, missing fuel… reported by the owner), before it is returned. It is
    paid to the owner with the rental; 0 cancels the withheld amount."""
    with transaction.atomic():
        location = LocationModel.objects.select_for_update().get(pk=location.pk)
        if not location.caution_gardee:
            raise LocationErreur("Cette location n'a pas de caution gardée par Kwa-Ba.")
        if location.statut != 'partenaire_assigne' or location.caution_restituee_le:
            raise LocationErreur("La caution a déjà été restituée, ou la location n'est plus en cours.")
        if location.debut > timezone.now():
            raise LocationErreur("Le véhicule n'a pas encore été remis : rien à retenir sur la caution.")
        if not 0 <= montant <= location.caution:
            raise LocationErreur(f"La retenue doit être comprise entre 0 et la caution ({location.caution} FCFA).")
        if montant and not motif.strip():
            raise LocationErreur("Indiquez le motif de la retenue : il est communiqué au voyageur.")
        location.caution_retenue, location.caution_motif = montant, motif.strip() if montant else ''
        location.save(update_fields=['caution_retenue', 'caution_motif'])
        VersementPartenaireModel.objects.filter(location=location, statut__in=('planifie', 'echoue')).update(
            **_montants_versement(location),
        )
    logger.info("Retenue de %s FCFA sur la caution de %s", montant, location.reference)
    return location


# --- Worker ------------------------------------------------------------------------------

def expirer() -> int:
    expirees = 0
    maintenant = timezone.now()
    for location in LocationModel.objects.filter(statut='en_attente_paiement', expire_le__lte=maintenant):
        for paiement in location.paiements.filter(statut='en_attente'):
            paiements.synchroniser_paiement(paiement)
        expirees += LocationModel.objects.filter(pk=location.pk, statut='en_attente_paiement').update(
            statut='annulee', annulee_par='expiration', annulee_le=maintenant,
        )
    return expirees


def restituer_cautions() -> int:
    """End of the damage reporting period: refunds the traveller the deposit minus the withheld amount."""
    params = ParametresLocationModel.courants()
    limite = timezone.now() - timedelta(hours=params.restitution_caution_heures if params else 24)
    restituees = 0
    a_restituer = LocationModel.objects.filter(
        statut='partenaire_assigne', caution_en_ligne=True, caution__gt=0, caution_restituee_le__isnull=True,
        fin__lte=limite,
    ).values_list('pk', flat=True)[:50]
    for pk in a_restituer:
        with transaction.atomic():
            loc = LocationModel.objects.select_for_update().get(pk=pk)
            if loc.caution_restituee_le:
                continue
            paiement = loc.paiements.filter(statut='reussi').order_by('cree_le').first()
            if paiement:
                paiements.rembourser(paiement, loc.caution - loc.caution_retenue, "Restitution de la caution")
            loc.caution_restituee_le = timezone.now()
            loc.save(update_fields=['caution_restituee_le'])
            restituees += 1
    return restituees


def envoyer_versements_partenaires() -> int:
    if not paiements.fedapay_actif():
        return 0
    envoyes = 0
    maintenant = timezone.now()
    # Late cancellation: the rental is cancelled, but the kept share is still paid pro rata
    statuts = ('partenaire_assigne', 'annulee')
    # Online deposit: the owner is paid once the deposit is settled (any withheld amount is added)
    dus = VersementPartenaireModel.objects.filter(
        statut='planifie', date_prevue__lte=maintenant, location__statut__in=statuts,
    ).exclude(
        location__caution_en_ligne=True, location__caution__gt=0, location__caution_restituee_le__isnull=True,
    ).select_related('partenaire')[:50]
    for v in dus:
        p = v.partenaire
        envoyes += paiements.envoyer_payout(
            v, mode=p.operateur_versement, numero=p.numero_versement, pays=p.pays_versement,
            email=p.email or settings.DEFAULT_FROM_EMAIL, titulaire=p.contact,
        )
    chauffeurs = VersementChauffeurLocationModel.objects.filter(
        statut='planifie', date_prevue__lte=maintenant, location__statut__in=statuts,
    ).select_related('chauffeur')[:50]
    for v in chauffeurs:
        c = v.chauffeur
        envoyes += paiements.envoyer_payout(
            v, mode=c.operateur_versement, numero=c.numero_versement, pays=c.pays_versement,
            email=c.email or settings.DEFAULT_FROM_EMAIL, titulaire=f"{c.prenom} {c.nom}",
        )
    for modele in (VersementPartenaireModel, VersementChauffeurLocationModel):
        for v in modele.objects.filter(statut='en_cours').exclude(payout_id='')[:50]:
            paiements.synchroniser_payout(v)
    # Owner and driver paid: the rental is finished
    (LocationModel.objects.filter(statut='partenaire_assigne')
     .filter(Q(versement__isnull=False) | Q(versement_chauffeur__isnull=False))
     .exclude(Q(versement__isnull=False) & ~Q(versement__statut__in=('envoye', 'annule')))
     .exclude(Q(versement_chauffeur__isnull=False) & ~Q(versement_chauffeur__statut__in=('envoye', 'annule')))
     .update(statut='terminee'))
    return envoyes


def passe() -> dict:
    from . import notifications  # local import: notifications imports the models

    return {
        'locations_expirees': expirer(),
        'cautions_restituees': restituer_cautions(),
        'versements_loueurs': envoyer_versements_partenaires(),
        'emails_locations': notifications.envoyer_notifications(),
    }
