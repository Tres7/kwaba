"""What field agents check, type by type.

Each type says where to find what waits for an agent (the "to do" queue), how to summarise it in a list and
detail it in its page. The modules that need field checks register their types at start-up (verifications for
listings and identity documents). Decisions stay in those modules: the mission only keeps their outcome.
"""
from dataclasses import dataclass
from typing import Callable

from django.core.exceptions import ValidationError
from django.db.models import QuerySet


@dataclass(frozen=True)
class TypeMission:
    code: str
    libelle: str            # "Listings to visit"
    a_faire: Callable[[], QuerySet]
    champ_cle: str          # field that identifies the checked object (the target of the mission)
    resume: Callable[[object], dict]
    detail: Callable[[object], dict]


TYPES: dict[str, TypeMission] = {}


def enregistrer(type_mission: TypeMission) -> None:
    TYPES[type_mission.code] = type_mission


def nom(utilisateur) -> str:
    """First name and last name, or the email otherwise."""
    if utilisateur is None:
        return 'Un agent'
    return f"{utilisateur.first_name} {utilisateur.last_name}".strip() or utilisateur.email


def cle(type_mission: TypeMission, objet) -> str:
    return str(getattr(objet, type_mission.champ_cle))


def a_faire(type_mission: TypeMission, cible: str):
    """The object if it still waits for an agent, otherwise None (already checked, removed, or invalid id)."""
    try:
        return type_mission.a_faire().filter(**{type_mission.champ_cle: cible}).first()
    except (ValueError, ValidationError):  # malformed id (invalid UUID)
        return None
