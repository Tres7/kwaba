"""Computation of a booking's amounts and of the cancellation scale (terms of sale, article 6.4 and appendix 1).

All amounts are integers in FCFA (the CFA franc has no subunit).
Example for 2.5 nights at 25,000 FCFA (62,500 FCFA) with an individual host:
    traveller's service fees 6 % = 3,750 → the traveller pays 66,250;
    host commission 8 % = 5,000 → the host receives 57,500; Kwa-Ba keeps 8,750 (before FedaPay fees).
"""
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

# Service fees paid by the traveller
FRAIS_VOYAGEUR = Decimal('0.06')
FRAIS_REDUITS = Decimal('0.03')  # Loyal customer and Stay Pack + Driver

# Commission paid by the host (set by the team, see ConditionsHoteModel)
COMMISSION_PARTICULIER = Decimal('0.08')
COMMISSION_HOTEL = Decimal('0.12')
COMMISSION_FONDATEUR = Decimal('0.05')
COMMISSION_HOTE = COMMISSION_PARTICULIER  # rate displayed by default

# Reference arrival time for the deadlines (cancellation scale, payout to the host)
HEURE_ARRIVEE = time(14, 0)
DELAI_VERSEMENT = timedelta(hours=24)

# Cancellation policies chosen by the host (terms of sale, appendix 1)
POLITIQUES = [('souple', 'Souple'), ('moderee', 'Modérée'), ('ferme', 'Ferme')]
POLITIQUE_PAR_DEFAUT = 'moderee'
# Cooling-off period offered (terms of sale, art. 10.3): cancellation within 48 h, at least 7 days before arrival
REFLEXION = timedelta(hours=48)
REFLEXION_AVANT_ARRIVEE = timedelta(days=7)
# Stays of at least 28 nights: the first month (30 nights) is not refundable less than 30 days before arrival
LONG_SEJOUR_NUITS = 28
PREMIER_MOIS_NUITS = 30


def arrondi(montant) -> int:
    return int(Decimal(montant).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class Montants:
    prix_nuits: int
    frais_service: int
    commission_hote: int

    @property
    def total(self) -> int:
        return self.prix_nuits + self.frais_service

    @property
    def montant_hote(self) -> int:
        return self.prix_nuits - self.commission_hote

    @property
    def revenu_kwaba(self) -> int:
        """Kwa-Ba's gross revenue: traveller's fees + host's commission (before payment provider fees)."""
        return self.frais_service + self.commission_hote

    @property
    def taux_frais(self) -> int:
        """Service fee rate in %, for display ("Service fees (6 %)")."""
        return round(self.frais_service * 100 / self.prix_nuits) if self.prix_nuits else 0


def calculer(prix_par_nuit, nuits: int, frais=FRAIS_VOYAGEUR, commission=COMMISSION_PARTICULIER) -> Montants:
    """Traveller's fees and host's commission: two separate deductions on the price of the nights, rounded to the
    franc (to the nearest, half up, like formatFcfa on the site)."""
    if Decimal(prix_par_nuit) <= 0:
        raise ValueError('Le prix par nuit doit être positif.')
    if int(nuits) != nuits or nuits < 1:
        raise ValueError('Le nombre de nuits doit être un entier au moins égal à 1.')
    prix_nuits = arrondi(Decimal(prix_par_nuit) * nuits)
    return Montants(
        prix_nuits=prix_nuits,
        frais_service=arrondi(prix_nuits * Decimal(frais)),
        commission_hote=arrondi(prix_nuits * Decimal(commission)),
    )


# --- Rates by host and traveller -------------------------------------------------------------

def conditions(hote):
    from .models import ConditionsHoteModel

    return ConditionsHoteModel.objects.filter(hote=hote).first()


def taux_commission(hote, jour=None) -> Decimal:
    """8 % (individual), 12 % (hotel), 5 % during the Founders Programme."""
    c = conditions(hote)
    if not c:
        return COMMISSION_PARTICULIER
    if c.categorie == 'hotel':
        return COMMISSION_HOTEL
    return COMMISSION_FONDATEUR if c.fondateur_le(jour or timezone.localdate()) else COMMISSION_PARTICULIER


def hotes_deja_visites(voyageur) -> set:
    """Hosts the traveller has already stayed with through Kwa-Ba (paid and finished stay): loyal customer rate."""
    from apps.hebergements import api as hebergements
    from apps.reservations.models import ReservationModel

    if not voyageur or not voyageur.is_authenticated:
        return set()
    sejours = (ReservationModel.objects.filter(guest=voyageur, status='confirmed', check_out__lte=timezone.localdate())
               .values_list('hebergement_id', flat=True))
    return set(hebergements.hotes_des_annonces(set(sejours)).values())


def taux_frais(voyageur, hote_id) -> Decimal:
    """6 %; 3 % for a loyal customer (new stay with the same host through Kwa-Ba)."""
    return FRAIS_REDUITS if hote_id in hotes_deja_visites(voyageur) else FRAIS_VOYAGEUR


def devis(prix_par_nuit, hote_id, nuits: int, voyageur=None, jour=None, nb_unites: int = 1) -> Montants:
    """Amounts of a stay with the rates of this host and this traveller: `nb_unites` units at `prix_par_nuit`."""
    return calculer(prix_par_nuit * nb_unites, nuits, frais=taux_frais(voyageur, hote_id),
                    commission=taux_commission(hote_id, jour))


def _annonce(reservation) -> dict:
    from apps.hebergements import api as hebergements

    return hebergements.fiche(reservation.hebergement_id, archivees=True) or {}


def montants_de(reservation, prix_par_nuit=None) -> Montants:
    """Frozen amounts of a booking (computed again for bookings older than online payment, from `prix_par_nuit` or
    the listing's current price)."""
    if reservation.prix_nuits is not None:
        return Montants(reservation.prix_nuits, reservation.frais_service, reservation.commission_hote)
    return calculer(prix_par_nuit if prix_par_nuit is not None else _annonce(reservation)['price_per_night'],
                    reservation.nights)


def arrivee(reservation) -> datetime:
    return timezone.make_aware(datetime.combine(reservation.check_in, HEURE_ARRIVEE))


def date_versement(reservation) -> datetime:
    return arrivee(reservation) + DELAI_VERSEMENT


# --- Cancellation by the traveller ------------------------------------------------------------------

@dataclass(frozen=True)
class Annulation:
    rembourse_voyageur: int  # amount given back to the traveller
    nuits_retenues: int      # share of the price of the nights kept (goes to the host, minus the commission)
    commission_hote: int = 0  # commission on the kept nights, at the booking's rate

    @property
    def montant_hote(self) -> int:
        return self.nuits_retenues - self.commission_hote


def _retenue(montants: Montants, nuits_retenues: int, frais_rendus: bool = False) -> Annulation:
    """The traveller loses `nuits_retenues` (and the service fees, unless `frais_rendus`)."""
    nuits_retenues = max(0, min(nuits_retenues, montants.prix_nuits))
    commission = arrondi(Decimal(nuits_retenues) * montants.commission_hote / montants.prix_nuits) if montants.prix_nuits else 0
    rendu = montants.prix_nuits - nuits_retenues + (montants.frais_service if frais_rendus else 0)
    return Annulation(rembourse_voyageur=rendu, nuits_retenues=nuits_retenues, commission_hote=commission)


def politique(reservation) -> str:
    return _annonce(reservation).get('politique_annulation') or POLITIQUE_PAR_DEFAUT


REGLES_POLITIQUES = {
    'souple': "remboursement intégral jusqu'à 24 heures avant l'arrivée ; ensuite, la première nuit est retenue",
    'moderee': "remboursement intégral jusqu'à 5 jours avant l'arrivée ; 50 % des nuits jusqu'à 24 heures avant ; "
               "aucun remboursement ensuite",
    'ferme': "remboursement intégral jusqu'à 30 jours avant l'arrivée ; 50 % des nuits jusqu'à 7 jours avant ; "
             "aucun remboursement ensuite",
}


def texte_politique(reservation) -> str:
    """Cancellation conditions of the booking, in one sentence (booking voucher, confirmation email)."""
    code = politique(reservation)
    return (f"Politique {dict(POLITIQUES)[code]} : {REGLES_POLITIQUES[code]}. Les frais de service ne sont rendus qu'avec un "
            "remboursement intégral. Annulation gratuite dans les 48 heures suivant la réservation si l'arrivée est dans "
            "7 jours ou plus.")


def bareme_voyageur(montants: Montants, reservation, maintenant: datetime | None = None) -> Annulation:
    """Cancellation by the traveller (terms of sale, article 10.3 and appendix 1):
    - cooling-off period: cancelled within 48 h of the booking and at least 7 days before arrival,
      everything is refunded;
    - stay of 28 nights or more: everything is refunded at least 30 days before arrival; afterwards, the first
      month is kept and the service fees retained;
    - otherwise, the policy chosen by the host:
      Flexible: full refund until 24 h before; afterwards, the first night is kept;
      Moderate: full refund until 5 days before; 50 % of the nights until 24 h before; nothing afterwards;
      Strict: full refund until 30 days before; 50 % of the nights until 7 days before; nothing afterwards.
    Service fees are only given back with a full refund.
    """
    maintenant = maintenant or timezone.now()
    delai = arrivee(reservation) - maintenant
    integral = Annulation(rembourse_voyageur=montants.total, nuits_retenues=0)
    if maintenant - reservation.created_at <= REFLEXION and delai >= REFLEXION_AVANT_ARRIVEE:
        return integral

    nuits = max(1, (reservation.check_out - reservation.check_in).days)
    if nuits >= LONG_SEJOUR_NUITS:
        if delai >= timedelta(days=30):
            return integral
        return _retenue(montants, arrondi(Decimal(montants.prix_nuits) * min(nuits, PREMIER_MOIS_NUITS) / nuits))

    moitie = arrondi(Decimal(montants.prix_nuits) / 2)
    match politique(reservation):
        case 'souple':
            if delai >= timedelta(hours=24):
                return integral
            return _retenue(montants, arrondi(Decimal(montants.prix_nuits) / nuits))
        case 'ferme':
            if delai >= timedelta(days=30):
                return integral
            if delai >= timedelta(days=7):
                return _retenue(montants, moitie)
            return _retenue(montants, montants.prix_nuits)
        case _:  # moderate
            if delai >= timedelta(days=5):
                return integral
            if delai >= timedelta(hours=24):
                return _retenue(montants, moitie)
            return _retenue(montants, montants.prix_nuits)
