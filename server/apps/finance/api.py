"""Public interface of the finance module (ADR-019, ADR-024): the only file other modules import.

The modules that move money (payments, payouts, refunds) write their lines here, in their own database transaction
(FIN-01.6), with plain data (Ligne); the back-office reads the reports. Never a model in or out.

    from apps.finance import api as finance
    finance.enregistrer([finance.Ligne(nature='T01', offre='COURTE_DUREE', montant=250000, sens=finance.ENTREE,
                                       compte_argent='FEDAPAY', tiers_type='hote', tiers_id=hote_id, …)],
                        origine='paiement')
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Iterable

from collections.abc import Callable

from apps.finance.application.registre import declarer
from apps.finance.domain.entities import ENTREE, SORTIE, Ecrivain, Ligne
from apps.finance.domain.exceptions import MouvementRefuse, RestitutionRefusee
from apps.finance.domain.rules import mois_de
from apps.finance.infrastructure.container import grand_livre_service, restitution_service

__all__ = [
    'ENTREE', 'SORTIE', 'Ligne', 'MouvementRefuse', 'RestitutionRefusee',
    # Writing
    'declarer_ecritures', 'enregistrer', 'contre_passer', 'rectifier', 'a_des_lignes',
    # Reference
    'mois_de', 'parametre',
    # Reports
    'balance_generale', 'cautions_detenues', 'controle_equilibre', 'controle_invariants', 'derniers_mouvements',
    'du_aux_partenaires',
    'ecritures', 'marge_par_offre', 'peut_on_cloturer', 'rapport', 'soldes_comptes_argent', 'synthese',
]


# --- Writing --------------------------------------------------------------------------------------------------------

def declarer_ecritures(nom: str, *, offres: Iterable[str], natures: Iterable[str],
                       ouvert: Callable[[], bool] = lambda: True) -> None:
    """Declares, at start-up (AppConfig.ready), the offers and natures a module writes, and whether it is open: a
    deployment refuses to go on if an open module would write to an inactive one (check finance.E001, invariant
    I14)."""
    declarer(Ecrivain(nom=nom, offres=frozenset(offres), natures=frozenset(natures), ouvert=ouvert))


def enregistrer(lignes: Iterable[Ligne], *, origine: str, par_id: uuid.UUID | None = None) -> list[int]:
    """Writes the lines, all or none, in the caller's transaction; the ids of the new lines (a line of an external
    event already written is skipped). Raises MouvementRefuse, and alerts the finance team."""
    return grand_livre_service().enregistrer(lignes, origine=origine, par_id=par_id)


def contre_passer(mouvement_id: int, *, motif: str, origine: str = 'correction',
                  par_id: uuid.UUID | None = None) -> int:
    """Cancels a line by an inverse line; the id of the inverse line."""
    return grand_livre_service().contre_passer(mouvement_id, motif=motif, origine=origine, par_id=par_id)


def rectifier(nature: str, nouveau_montant: int, *, motif: str, origine: str, reservation_id=None, transfert_id=None,
              location_id=None, par_id: uuid.UUID | None = None) -> list[int]:
    """Brings the amount of a nature for a booking, a transfer or a rental to `nouveau_montant`, by inverse lines and
    a new line; the ids of the lines written."""
    objet = {'reservation_id': reservation_id, 'transfert_id': transfert_id, 'location_id': location_id}
    return grand_livre_service().rectifier(nature, nouveau_montant, motif=motif, origine=origine, objet=objet,
                                           par_id=par_id)


def a_des_lignes(*, externe_reference: str | None = None, reservation_id=None, transfert_id=None,
                 location_id=None) -> bool:
    """Is there a line of this external event, or of this booking, transfer or rental, in the ledger? Money older than
    the ledger has none: it is not written afterwards."""
    return grand_livre_service().a_des_lignes(externe_reference=externe_reference, reservation_id=reservation_id,
                                              transfert_id=transfert_id, location_id=location_id)


def parametre(cle: str) -> Decimal:
    """Value in force of a steered parameter; ValueError if unknown or inactive."""
    return grand_livre_service().parametre(cle)


# --- Reports --------------------------------------------------------------------------------------------------------

def controle_invariants() -> list[dict]:
    """One row per invariant (I5, I8 to I13): {invariant, libelle, anomalies}, 0 = respected."""
    return restitution_service().controle_invariants()


def peut_on_cloturer(mois: date) -> list[dict]:
    """« Can this month be locked? »: {controle, resultat, verdict (OK / REFUSE), que_faire} for six checks."""
    return restitution_service().peut_on_cloturer(mois)


def synthese(debut: date, fin: date, axe1: str = 'mois', axe2: str | None = None, familles=None,
             offres=None) -> list[dict]:
    """Signed totals of [debut, fin] on one or two axes of finance_axe: {axe1, axe2, nb, montant}."""
    return restitution_service().synthese(debut, fin, axe1, axe2, familles, offres)


def rapport(code: str, debut: date, fin: date) -> list[dict]:
    """A saved report of finance_rapport, on [debut, fin]."""
    return restitution_service().rapport(code, debut, fin)


def du_aux_partenaires() -> list[dict]:
    """What Kwa-Ba owes each partner now: {tiers_type, tiers_id, solde_du}."""
    return restitution_service().du_aux_partenaires()


def derniers_mouvements(limite: int = 50) -> list[dict]:
    """The latest lines of the ledger, newest first (500 at most)."""
    return restitution_service().derniers_mouvements(limite)


def cautions_detenues() -> list[dict]:
    """Deposits held for the travellers: {reservation_id, location_id, solde_detenu}."""
    return restitution_service().cautions_detenues()


def soldes_comptes_argent() -> dict[str, int]:
    """Balance of each money account in the ledger."""
    return restitution_service().soldes_comptes_argent()


def balance_generale(mois: date | None = None) -> list[dict]:
    """Trial balance by SYSCOHADA account, for one month or every month."""
    return restitution_service().balance_generale(mois)


def controle_equilibre() -> list[dict]:
    """Debits and credits of each month: the gap must be zero."""
    return restitution_service().controle_equilibre()


def marge_par_offre(mois: date) -> list[dict]:
    """Revenue, variable costs and margin of each offer for a month."""
    return restitution_service().marge_par_offre(mois)


def ecritures(mois: date) -> list[dict]:
    """Double-entry lines of a month: two per movement, same amount, opposite directions."""
    return restitution_service().ecritures(mois)
