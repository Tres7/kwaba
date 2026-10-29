"""Bookings seen by the listings module (availability, closures, archiving), without reading their tables.

The reservations module registers its provider at start-up (AppConfig.ready).
"""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class FournisseurReservations:
    # (hebergement_ids, debut, fin, exclure) -> active bookings over the period:
    # [{'id', 'hebergement_id', 'type_logement_id', 'check_in', 'check_out', 'nb_unites'}]
    actives: Callable[..., list[dict]]
    # (hebergement_id, debut, fin) -> the same with 'reference', 'voyageur' and 'statut' (host calendar)
    detail: Callable[..., list[dict]]
    # hebergement_id -> a paid stay is upcoming or in progress
    sejour_paye_a_venir: Callable[[object], bool]
    # hebergement_id -> cancels the bookings waiting for payment; [{'id', 'email', 'prenom', 'check_in', 'check_out'}]
    annuler_en_attente: Callable[[object], list[dict]]
    # type_logement_id -> at least one booking (of any status) was made on this unit type
    type_reserve: Callable[[object], bool]


_fournisseur: FournisseurReservations | None = None


def enregistrer(fournisseur: FournisseurReservations) -> None:
    global _fournisseur
    _fournisseur = fournisseur


def reservations() -> FournisseurReservations:
    if _fournisseur is None:
        raise RuntimeError("Aucun fournisseur de réservations enregistré (apps.reservations.apps.ready).")
    return _fournisseur
