"""Shared queue of the field agents.

An agent takes a mission ("I'll handle it"): it disappears from the others' queue, and they alone can decide.
They can release it if they cannot handle it. An administrator does everything an agent does, and in addition
can release another agent's mission or decide in their place; the reverse does not exist (the back-office stays
reserved for administrators).
"""
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import MissionModel
from .types import TYPES, TypeMission, a_faire, nom

ROLES_AGENTS = ('agent', 'admin')


class MissionErreur(Exception):
    """Message that can be shown to the agent."""

    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.code = code


def type_mission(code: str) -> TypeMission:
    if code not in TYPES:
        raise MissionErreur('Type de mission inconnu.', 404)
    return TYPES[code]


def est_admin(utilisateur) -> bool:
    return utilisateur.role == 'admin'


def en_cours(code: str, cible: str) -> MissionModel | None:
    return MissionModel.objects.filter(type=code, cible=str(cible), statut='en_cours').select_related('agent').first()


def prendre(code: str, cible: str, agent) -> MissionModel:
    """"I'll handle it": the mission belongs to this agent until their decision or until they release it."""
    tm = type_mission(code)
    objet = a_faire(tm, cible)
    if objet is None:
        raise MissionErreur("Cette mission n'est plus à faire (déjà traitée ou retirée).", 404)
    actuelle = en_cours(code, cible)
    if actuelle:
        if actuelle.agent_id == agent.pk:
            return actuelle
        raise MissionErreur(f"{nom(actuelle.agent)} s'en occupe déjà.", 409)
    resume = tm.resume(objet)
    try:
        with transaction.atomic():
            return MissionModel.objects.create(
                type=code, cible=str(cible), agent=agent, titre=resume['titre'][:200],
                sous_titre=(resume.get('sous_titre') or '')[:200], ville=(resume.get('ville') or '')[:100])
    except IntegrityError:
        # Another agent took it at the same moment (uniqueness constraint of ongoing missions)
        raise MissionErreur("Un autre agent vient de la prendre.", 409) from None


def liberer(code: str, cible: str, utilisateur) -> MissionModel:
    """Releases an ongoing mission: it goes back to the shared queue. An agent only releases their own."""
    type_mission(code)
    mission = en_cours(code, cible)
    if not mission:
        raise MissionErreur("Aucune mission en cours.", 404)
    if mission.agent_id != utilisateur.pk and not est_admin(utilisateur):
        raise MissionErreur(f"Seul {nom(mission.agent)} ou un administrateur peut relâcher cette mission.", 403)
    mission.statut, mission.terminee_le = 'liberee', timezone.now()
    mission.save(update_fields=['statut', 'terminee_le'])
    return mission


def verifier_peut_decider(code: str, cible: str, utilisateur) -> None:
    """Before a decision: refused if another agent took the mission (an administrator can always decide)."""
    mission = en_cours(code, cible)
    if mission and mission.agent_id != utilisateur.pk and not est_admin(utilisateur):
        raise MissionErreur(f"{nom(mission.agent)} s'occupe de cette mission : lui seul peut décider.", 409)


def terminer(code: str, cible: str, utilisateur, *, decision: str, titre: str, sous_titre: str = '', ville: str = ''):
    """After the decision (in the same transaction): the ongoing mission is closed, or created closed if nobody
    had taken it, so that the agent's history is complete."""
    mission = en_cours(code, cible) or MissionModel(type=code, cible=str(cible), agent=utilisateur, titre=titre[:200],
                                                     sous_titre=sous_titre[:200], ville=ville[:100])
    # The one who decides (an administrator can decide on an agent's mission)
    mission.agent = utilisateur
    mission.statut, mission.decision, mission.terminee_le = 'terminee', decision, timezone.now()
    mission.save()
    return mission
