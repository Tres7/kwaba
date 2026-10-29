"""What field agents check, type by type.

Each type says where to find what waits for an agent (the "to do" queue), how to summarise it in a list and
detail it in its page. The modules that need field checks register their types at start-up (verifications for
listings and identity documents). Decisions stay in those modules: the mission only keeps their outcome.
"""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class TypeMission:
    code: str
    libelle: str            # "Listings to visit"
    a_faire: Callable[[], list]
    identifiant: Callable[[object], object]  # identifies the checked object (the target of the mission)
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
    return str(type_mission.identifiant(objet))


def a_faire(type_mission: TypeMission, cible: str):
    """The object if it still waits for an agent, otherwise None (already checked, removed, or invalid id)."""
    return next((objet for objet in type_mission.a_faire() if cle(type_mission, objet) == str(cible)), None)
