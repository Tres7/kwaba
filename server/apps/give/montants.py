"""Supported causes, donation amounts and transfer schedule.

Kwa-Ba takes no commission on donations. Only the fees of the payment provider
(FedaPay, PayPal) apply; the donor chooses to add them to their donation (the NGO then receives
100 % of the chosen amount) or to have them deducted from the transferred amount.

Example for a donation of 2,000 FCFA (3 % fees):
    fees added     → the donor pays 2,062, the NGO receives 2,000
    fees deducted  → the donor pays 2,000, the NGO receives 1,940
"""
import math
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CAUSES = {
    'education': {'nom': 'Éducation', 'description': "Écoles, fournitures, bourses et soutien scolaire."},
    'sante': {'nom': 'Santé', 'description': "Soins, centres de santé, prévention et accès aux médicaments."},
    'eau': {'nom': "Accès à l'eau", 'description': "Forages, puits, assainissement et hygiène."},
    'environnement': {'nom': 'Environnement', 'description': "Reboisement, gestion des déchets, protection des côtes."},
}
CAUSE_CHOICES = [(code, c['nom']) for code, c in CAUSES.items()]

# Average fees of the payment providers (Mobile Money, card, PayPal), to adjust to the FedaPay contract
FRAIS_PAIEMENT = Decimal('0.03')
COMMISSION_KWABA = Decimal('0')  # free for partner NGOs at launch

MONTANTS_SUGGERES = [500, 2000, 3000, 5000]
MONTANT_MIN = 500
MONTANT_MAX = 1_000_000

# A month's donations are transferred to the NGO at the latest on the 10th of the following month
JOUR_REVERSEMENT = 10


@dataclass(frozen=True)
class MontantsDon:
    don: int  # amount chosen by the donor
    frais: int  # payment provider fees
    total: int  # charged amount
    montant_ong: int  # amount transferred to the NGO


def calculer(montant: int, couvre_frais: bool) -> MontantsDon:
    if couvre_frais:
        # Fees apply to the charged amount: it is rounded up to the franc so that the NGO receives everything
        total = math.ceil(Decimal(montant) / (1 - FRAIS_PAIEMENT))
        return MontantsDon(don=montant, frais=total - montant, total=total, montant_ong=montant)
    frais = int((Decimal(montant) * FRAIS_PAIEMENT).to_integral_value(ROUND_HALF_UP))  # like Math.round on the site
    return MontantsDon(don=montant, frais=frais, total=montant, montant_ong=montant - frais)


def debut_du_mois(jour: date) -> date:
    return jour.replace(day=1)


def mois_suivant(jour: date) -> date:
    return date(jour.year + jour.month // 12, jour.month % 12 + 1, 1)


def date_reversement(jour_du_don: date) -> date:
    """Deadline of the transfer to the NGO for a donation made on that day."""
    return mois_suivant(jour_du_don).replace(day=JOUR_REVERSEMENT)
