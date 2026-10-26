"""Vehicle categories, transfer price computation and timing rules.

Base prices per airport and per category are in TarifTransfertModel (editable
in the Django admin); this module applies the shared rules.
"""
from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

CATEGORIES = {
    'berline': {'nom': 'Berline', 'description': 'Toyota Corolla ou similaire, climatisée', 'passagers': 3, 'bagages': 3},
    'confort': {'nom': 'SUV confort', 'description': 'Toyota RAV4 ou similaire, plus d\'espace', 'passagers': 4, 'bagages': 4},
    'van': {'nom': 'Minibus', 'description': 'Toyota Hiace ou similaire, pour les groupes', 'passagers': 7, 'bagages': 8},
}
CATEGORIE_CHOICES = [(code, c['nom']) for code, c in CATEGORIES.items()]

# Share of the price kept by Kwa-Ba, the rest goes to the partner driver (grid of 18 October 2026)
COMMISSION_CHAUFFEUR = Decimal('0.15')

# Assigning a driver takes time: booking at the latest 6 h before arrival
DELAI_MIN_RESERVATION = timedelta(hours=6)
# Free cancellation until 24 h before arrival; afterwards the driver is paid
DELAI_ANNULATION_GRATUITE = timedelta(hours=24)
# The driver is paid 24 h after the pick-up (time to report a problem)
DELAI_VERSEMENT = timedelta(hours=24)
# Free waiting time of the driver after landing
ATTENTE_INCLUSE_MINUTES = 60


@dataclass(frozen=True)
class Prix:
    prix: int
    commission: int

    @property
    def montant_chauffeur(self) -> int:
        return self.prix - self.commission


def calculer(prix_base: int) -> Prix:
    """Same price by day and by night (the night surcharge was removed on 23 October 2026)."""
    prix = int(prix_base)
    commission = int((Decimal(prix) * COMMISSION_CHAUFFEUR).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    return Prix(prix=prix, commission=commission)


def capacite_suffisante(categorie: str, passagers: int, bagages: int) -> str | None:
    """Explains why the vehicle does not fit, or None."""
    c = CATEGORIES[categorie]
    if passagers > c['passagers']:
        return f"{c['passagers']} passagers maximum"
    if bagages > c['bagages']:
        return f"{c['bagages']} bagages maximum"
    return None
