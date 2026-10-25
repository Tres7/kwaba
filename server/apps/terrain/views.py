from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.securite.audit import journaliser

from . import services
from .models import MissionModel
from .types import TYPES, a_faire, cle

VUES = ('a_faire', 'miennes', 'equipe')
LIMITE = 200


class EstAgent(IsAuthenticated):
    """Agents de terrain et administrateurs : rôle lu en base à chaque requête."""
    message = "Réservé aux agents de terrain."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in services.ROLES_AGENTS


def _personne(utilisateur) -> dict | None:
    if utilisateur is None:
        return None
    return {'id': str(utilisateur.pk), 'nom': services.nom(utilisateur)}


def _mission_json(mission: MissionModel | None, moi) -> dict | None:
    if mission is None:
        return None
    return {
        'id': str(mission.id), 'statut': mission.statut, 'decision': mission.decision, 'agent': _personne(mission.agent),
        'moi': mission.agent_id == moi.pk, 'prise_le': mission.prise_le, 'terminee_le': mission.terminee_le,
    }


def _en_cours_par_type(codes) -> dict[str, dict[str, MissionModel]]:
    missions = MissionModel.objects.filter(type__in=codes, statut='en_cours').select_related('agent')
    par_type: dict[str, dict[str, MissionModel]] = {code: {} for code in codes}
    for m in missions:
        par_type[m.type][m.cible] = m
    return par_type


def _codes(request) -> list[str]:
    demande = request.query_params.get('type', '')
    return [demande] if demande in TYPES else list(TYPES)


class TableauView(APIView):
    """GET : accueil de l'espace agent. Par type : missions libres, les miennes, celles des autres agents."""
    permission_classes = [EstAgent]

    def get(self, request):
        codes = list(TYPES)
        en_cours = _en_cours_par_type(codes)
        types = []
        for code in codes:
            tm = TYPES[code]
            cibles = {str(c) for c in tm.a_faire().values_list(tm.champ_cle, flat=True)}
            prises = {cible: m for cible, m in en_cours[code].items() if cible in cibles}
            miennes = sum(1 for m in prises.values() if m.agent_id == request.user.pk)
            types.append({'type': code, 'libelle': tm.libelle, 'libres': len(cibles) - len(prises),
                          'miennes': miennes, 'equipe': len(prises) - miennes})
        debut_mois = timezone.localdate().replace(day=1)
        faites = MissionModel.objects.filter(agent=request.user, statut='terminee', terminee_le__date__gte=debut_mois)
        return Response({
            'types': types,
            'faites_ce_mois': faites.count(),
            'admin': services.est_admin(request.user),
        })


class MissionsView(APIView):
    """GET ?vue=a_faire|miennes|equipe|historique&type=&q= : la file commune, mes missions, celles de l'équipe, ou
    l'historique (le mien ; tout le monde pour un administrateur). Les plus anciennes d'abord, sauf l'historique."""
    permission_classes = [EstAgent]

    def get(self, request):
        vue = request.query_params.get('vue', 'a_faire')
        q = request.query_params.get('q', '').strip().lower()
        if vue == 'historique':
            return Response(self._historique(request, q))
        if vue not in VUES:
            return Response({'vue': ['Vue inconnue.']}, status=status.HTTP_400_BAD_REQUEST)

        codes = _codes(request)
        en_cours = _en_cours_par_type(codes)
        resultats = []
        for code in codes:
            tm = TYPES[code]
            for objet in tm.a_faire()[:LIMITE]:
                cible = cle(tm, objet)
                mission = en_cours[code].get(cible)
                if vue == 'a_faire' and mission:
                    continue
                if vue == 'miennes' and (not mission or mission.agent_id != request.user.pk):
                    continue
                if vue == 'equipe' and (not mission or mission.agent_id == request.user.pk):
                    continue
                resume = tm.resume(objet)
                if q and q not in f"{resume['titre']} {resume.get('ville', '')} {resume.get('adresse', '')}".lower():
                    continue
                resultats.append({'type': code, 'type_libelle': tm.libelle, 'cible': cible, **resume,
                                  'mission': _mission_json(mission, request.user)})
        resultats.sort(key=lambda r: r['date'])
        return Response({'results': resultats, 'count': len(resultats)})

    def _historique(self, request, q: str) -> dict:
        qs = MissionModel.objects.filter(statut='terminee').select_related('agent').order_by('-terminee_le')
        if not services.est_admin(request.user) or request.query_params.get('agent') == 'moi':
            qs = qs.filter(agent=request.user)
        codes = _codes(request)
        qs = qs.filter(type__in=codes)
        if q:
            qs = qs.filter(titre__icontains=q) | qs.filter(ville__icontains=q)
        resultats = [{
            'type': m.type, 'type_libelle': TYPES[m.type].libelle if m.type in TYPES else m.get_type_display(),
            'cible': m.cible, 'titre': m.titre, 'sous_titre': m.sous_titre, 'ville': m.ville,
            'date': m.terminee_le, 'mission': _mission_json(m, request.user),
        } for m in qs[:LIMITE]]
        return {'results': resultats, 'count': len(resultats)}


class MissionView(APIView):
    """GET : fiche d'une mission à faire (de quoi faire le contrôle) et ce que je peux faire dessus."""
    permission_classes = [EstAgent]

    def get(self, request, type_mission, cible):
        try:
            tm = services.type_mission(type_mission)
        except services.MissionErreur as exc:
            return Response({'detail': str(exc)}, status=exc.code)
        objet = a_faire(tm, cible)
        if objet is None:
            return Response({'detail': "Cette mission n'est plus à faire (déjà traitée ou retirée)."},
                            status=status.HTTP_404_NOT_FOUND)
        mission = services.en_cours(type_mission, cible)
        moi, admin = request.user, services.est_admin(request.user)
        a_moi = bool(mission and mission.agent_id == moi.pk)
        return Response({
            'type': type_mission, 'type_libelle': tm.libelle, 'cible': cible, **tm.resume(objet), **tm.detail(objet),
            'mission': _mission_json(mission, moi),
            'droits': {
                'prendre': mission is None,
                'liberer': bool(mission) and (a_moi or admin),
                # Libre ou à moi ; un administrateur décide toujours
                'decider': mission is None or a_moi or admin,
            },
        })


class _ActionMission(APIView):
    permission_classes = [EstAgent]
    action = ''

    def post(self, request, type_mission, cible):
        try:
            mission = getattr(services, self.action)(type_mission, cible, request.user)
        except services.MissionErreur as exc:
            return Response({'detail': str(exc)}, status=exc.code)
        journaliser(f'mission_{"prise" if self.action == "prendre" else "relachee"}', request, utilisateur=request.user,
                    type=type_mission, cible=str(cible), agent=str(mission.agent_id or ''))
        return Response(_mission_json(mission, request.user))


class PrendreView(_ActionMission):
    """POST : « Je m'en occupe » (409 si un autre agent l'a déjà prise)."""
    action = 'prendre'


class LibererView(_ActionMission):
    """POST : relâcher la mission, qui revient dans la file commune (la mienne ; n'importe laquelle pour un admin)."""
    action = 'liberer'
