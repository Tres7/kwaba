"""Modules that write movements in the ledger, declared at start-up (AppConfig.ready) through
finance.api.declarer_ecritures. The finance module never imports them."""
from apps.finance.domain.entities import Ecrivain

ECRIVAINS: dict[str, Ecrivain] = {}


def declarer(ecrivain: Ecrivain) -> None:
    ECRIVAINS[ecrivain.nom] = ecrivain
