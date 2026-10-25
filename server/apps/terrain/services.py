"""File commune des agents de terrain.

Un agent prend une mission (« Je m'en occupe ») : elle disparaît de la file des autres, et lui seul peut décider.
Il peut la relâcher s'il ne peut pas s'en occuper. Un administrateur fait tout ce que fait un agent, et en plus il
peut relâcher la mission d'un autre ou décider à sa place ; l'inverse n'existe pas (le back-office reste réservé
aux administrateurs).
"""
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import MissionModel
from .types import TYPES, TypeMission, a_faire, nom

ROLES_AGENTS = ('agent', 'admin')


class MissionErreur(Exception):
    """Message affichable à l'agent."""

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
    """« Je m'en occupe » : la mission est à cet agent jusqu'à sa décision ou jusqu'à ce qu'il la relâche."""
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
        # Un autre agent l'a prise au même instant (contrainte d'unicité des missions en cours)
        raise MissionErreur("Un autre agent vient de la prendre.", 409) from None


def liberer(code: str, cible: str, utilisateur) -> MissionModel:
    """Relâche une mission en cours : elle revient dans la file commune. Un agent ne relâche que les siennes."""
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
    """Avant une décision : refusée si un autre agent a pris la mission (un administrateur peut toujours décider)."""
    mission = en_cours(code, cible)
    if mission and mission.agent_id != utilisateur.pk and not est_admin(utilisateur):
        raise MissionErreur(f"{nom(mission.agent)} s'occupe de cette mission : lui seul peut décider.", 409)


def terminer(code: str, cible: str, utilisateur, *, decision: str, titre: str, sous_titre: str = '', ville: str = ''):
    """Après la décision (dans la même transaction) : la mission en cours est close, ou créée close si personne ne
    l'avait prise, pour que l'historique de l'agent soit complet."""
    mission = en_cours(code, cible) or MissionModel(type=code, cible=str(cible), agent=utilisateur, titre=titre[:200],
                                                     sous_titre=sous_titre[:200], ville=ville[:100])
    # Celui qui décide (un administrateur peut décider sur la mission d'un agent)
    mission.agent = utilisateur
    mission.statut, mission.decision, mission.terminee_le = 'terminee', decision, timezone.now()
    mission.save()
    return mission
