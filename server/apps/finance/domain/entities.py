"""What the ledger knows (FIN-01): movements qualified by a nature, an offer and a third party. It ignores what a
booking, an experience or a ticket is (extensibility rule 6). Pure Python, no Django."""
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

ENTREE, SORTIE = 'entree', 'sortie'
SENS = (ENTREE, SORTIE)
# States of an accounting month (FIN-08): nothing is written any more in a locked month
PERIODE_OUVERTE, PERIODE_EN_CONTROLE, PERIODE_VERROUILLEE = 'ouverte', 'en_controle', 'verrouillee'

# Families whose lines need what they refer to: partner money is owed to an identified person (FIN-07.1), a deposit
# is held for a booking or a car rental (FIN-05.1)
FONDS_DE_TIERS, CAUTION = 'T', 'C'
# Deposit withheld for damage: needs the reason and the reference of the decision (FIN-05.5)
CAUTION_RETENUE = 'C03'


@dataclass(frozen=True)
class Ligne:
    """One movement to write. `montant`: whole FCFA, positive (the direction carries the sign); codes are those of
    the reference tables (nature, offre, compte_argent, tiers_type, moyen_paiement)."""
    nature: str
    offre: str
    montant: int
    sens: str
    compte_argent: str
    tiers_type: str | None = None
    tiers_id: uuid.UUID | str | None = None
    moyen_paiement: str | None = None
    piece_reference: str | None = None
    # Id of the provider's transaction: the same event is written once (FIN-01.7)
    externe_reference: str | None = None
    reservation_id: uuid.UUID | str | None = None
    ligne_reservation_id: uuid.UUID | str | None = None
    prestation_type: str | None = None
    transfert_id: uuid.UUID | str | None = None
    location_id: uuid.UUID | str | None = None
    date_evenement: datetime | None = None
    motif: str | None = None
    devise: str = 'XOF'
    metadonnees: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Nature:
    code: str
    famille: str
    sens_attendu: str | None
    actif: bool


@dataclass(frozen=True)
class Referentiels:
    """The reference rows a batch of lines uses: natures, and the active flag of each offer, money account, kind of
    third party and payment method (a missing code is unknown)."""
    natures: dict[str, Nature]
    offres: dict[str, bool]
    comptes_argent: dict[str, bool]
    tiers_types: dict[str, bool]
    moyens_paiement: dict[str, bool]


@dataclass(frozen=True)
class Ecriture:
    """A line checked and ready to be written: the line, its accounting month, who and what wrote it, and for an
    inverse line the line it cancels."""
    ligne: Ligne
    date_evenement: datetime
    mois: date
    origine: str
    par_id: uuid.UUID | None = None
    annule_mouvement_id: int | None = None


@dataclass(frozen=True)
class Mouvement:
    """A line already in the ledger."""
    id: int
    ligne: Ligne
    mois: date
    origine: str
    annule_mouvement_id: int | None


@dataclass(frozen=True)
class Ecrivain:
    """A module that writes movements in the ledger: the offers and natures it uses, and whether it is open now (its
    module switch). Declared at start-up, so that a module open with an inactive offer or nature is seen before its
    first payment fails."""
    nom: str
    offres: frozenset[str]
    natures: frozenset[str]
    ouvert: Callable[[], bool] = lambda: True
