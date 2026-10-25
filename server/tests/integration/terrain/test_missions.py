"""Espace agent de terrain : file commune (prendre, relâcher, décider) et partage des droits entre agents et admins.

Un administrateur fait tout ce que fait un agent (et peut relâcher ou décider sur la mission d'un autre) ; un agent ne
fait jamais ce que fait un administrateur.
"""
import json

import pytest

from apps.terrain.models import MissionModel
from apps.verifications.models import PieceIdentiteModel

TABLEAU = '/api/v1/agent/tableau/'
MISSIONS = '/api/v1/agent/missions/'
VISITES = '/api/v1/verifications/visites/'
IDENTITES = '/api/v1/verifications/identites/'
TOUT_CONFORME = {'identite': True, 'adresse': True, 'photos': True, 'equipements': True}


@pytest.fixture
def agents(make_user):
    return make_user(role='agent', first_name='Kofi', last_name='Mensah'), make_user(role='agent', first_name='Afi')


@pytest.fixture
def admin(make_user):
    return make_user(role='admin')


@pytest.fixture
def annonce(make_user, make_hebergement):
    """Annonce prête pour une visite : identité de l'hôte vérifiée."""
    hote = make_user(role='hote', phone='+22890000001')
    PieceIdentiteModel.objects.create(hote=hote, type_piece='cni', statut='verifiee')
    return make_hebergement(host=hote, name='Villa des cocotiers', statut_verification='en_attente', city='Lomé')


@pytest.fixture
def piece(make_user):
    hote = make_user(role='hote', phone='+22890000002', first_name='Ama', last_name='Koffi')
    return PieceIdentiteModel.objects.create(hote=hote, type_piece='passeport', statut='soumise')


def _url(type_mission, cible, action=''):
    return f'{MISSIONS}{type_mission}/{cible}/{action + "/" if action else ""}'


def _cibles(client, vue):
    return [(r['type'], r['cible']) for r in client.get(MISSIONS, {'vue': vue}).data['results']]


def _valider(client, annonce):
    return client.post(f'{VISITES}{annonce.id}/decision/',
                       {'decision': 'validee', 'controles': json.dumps(TOUT_CONFORME), 'commentaire': ''}, format='multipart')


class TestDroits:
    @pytest.mark.parametrize('role', ['voyageur', 'hote'])
    def test_agent_space_is_for_agents_and_admins_only(self, client_for, make_user, api_client, role):
        assert client_for(make_user(role=role)).get(TABLEAU).status_code == 403
        assert client_for(make_user(role=role)).get(MISSIONS).status_code == 403
        assert api_client.get(TABLEAU).status_code == 401

    def test_admin_does_everything_an_agent_does(self, client_for, admin, annonce):
        client = client_for(admin)
        assert client.get(TABLEAU).status_code == 200
        assert client.post(_url('logement', annonce.id, 'prendre')).status_code == 200
        assert _valider(client, annonce).status_code == 201

    @pytest.mark.parametrize('url', ['/api/v1/admin/hebergements/', '/api/v1/admin/users/'])
    def test_agent_never_reaches_the_back_office(self, client_for, agents, url):
        assert client_for(agents[0]).get(url).status_code == 403


class TestFileCommune:
    def test_a_mission_taken_by_an_agent_leaves_the_shared_queue(self, client_for, agents, annonce, piece):
        kofi, afi = (client_for(a) for a in agents)
        assert set(_cibles(afi, 'a_faire')) == {('logement', str(annonce.id)), ('piece', str(piece.hote_id))}

        reponse = kofi.post(_url('logement', annonce.id, 'prendre'))
        assert reponse.status_code == 200 and reponse.data['moi'] is True

        assert _cibles(afi, 'a_faire') == [('piece', str(piece.hote_id))]
        assert _cibles(afi, 'equipe') == [('logement', str(annonce.id))]
        assert _cibles(kofi, 'miennes') == [('logement', str(annonce.id))]
        # Prendre deux fois sa propre mission ne change rien
        assert kofi.post(_url('logement', annonce.id, 'prendre')).status_code == 200
        assert MissionModel.objects.filter(statut='en_cours').count() == 1

    def test_only_the_agent_who_took_it_can_decide(self, client_for, agents, annonce):
        kofi, afi = (client_for(a) for a in agents)
        kofi.post(_url('logement', annonce.id, 'prendre'))

        refus = afi.post(_url('logement', annonce.id, 'prendre'))
        assert refus.status_code == 409 and 'Kofi Mensah' in refus.data['detail']
        assert _valider(afi, annonce).status_code == 409
        annonce.refresh_from_db()
        assert annonce.statut_verification == 'en_attente'

        assert _valider(kofi, annonce).status_code == 201
        mission = MissionModel.objects.get()
        assert (mission.statut, mission.decision, mission.agent) == ('terminee', 'validee', agents[0])
        assert _cibles(kofi, 'historique') == [('logement', str(annonce.id))]
        assert _cibles(afi, 'historique') == []

    def test_an_agent_releases_only_his_missions_and_an_admin_any(self, client_for, agents, admin, annonce):
        kofi, afi = (client_for(a) for a in agents)
        kofi.post(_url('logement', annonce.id, 'prendre'))

        assert afi.post(_url('logement', annonce.id, 'liberer')).status_code == 403
        assert client_for(admin).post(_url('logement', annonce.id, 'liberer')).status_code == 200
        assert _cibles(afi, 'a_faire') == [('logement', str(annonce.id))]

        afi.post(_url('logement', annonce.id, 'prendre'))
        assert afi.post(_url('logement', annonce.id, 'liberer')).status_code == 200
        assert list(MissionModel.objects.values_list('statut', flat=True)) == ['liberee', 'liberee']

    def test_an_admin_can_decide_on_an_agent_mission(self, client_for, agents, admin, annonce):
        client_for(agents[0]).post(_url('logement', annonce.id, 'prendre'))
        assert _valider(client_for(admin), annonce).status_code == 201
        assert MissionModel.objects.get().agent == admin

    def test_deciding_without_taking_the_mission_still_fills_the_history(self, client_for, agents, piece):
        kofi = client_for(agents[0])
        assert kofi.post(f'{IDENTITES}{piece.hote_id}/decision/', {'decision': 'verifiee'}).status_code == 200
        mission = MissionModel.objects.get()
        assert (mission.type, mission.titre, mission.decision, mission.statut) == ('piece', 'Ama Koffi', 'validee', 'terminee')
        assert _cibles(kofi, 'historique') == [('piece', str(piece.hote_id))]

    def test_an_admin_sees_everyone_history(self, client_for, agents, admin, piece):
        client_for(agents[0]).post(f'{IDENTITES}{piece.hote_id}/decision/', {'decision': 'verifiee'})
        assert _cibles(client_for(admin), 'historique') == [('piece', str(piece.hote_id))]
        assert client_for(admin).get(MISSIONS, {'vue': 'historique', 'agent': 'moi'}).data['count'] == 0


class TestFiche:
    def test_the_card_says_what_i_can_do(self, client_for, agents, admin, annonce):
        kofi, afi = (client_for(a) for a in agents)
        libre = afi.get(_url('logement', annonce.id)).data
        assert libre['droits'] == {'prendre': True, 'liberer': False, 'decider': True}
        assert libre['titre'] == 'Villa des cocotiers' and set(libre['controles']) == set(TOUT_CONFORME)

        kofi.post(_url('logement', annonce.id, 'prendre'))
        assert afi.get(_url('logement', annonce.id)).data['droits'] == {'prendre': False, 'liberer': False, 'decider': False}
        assert kofi.get(_url('logement', annonce.id)).data['droits'] == {'prendre': False, 'liberer': True, 'decider': True}
        assert client_for(admin).get(_url('logement', annonce.id)).data['droits'] == {
            'prendre': False, 'liberer': True, 'decider': True}

    def test_unknown_or_finished_missions(self, client_for, agents, make_hebergement):
        kofi = client_for(agents[0])
        assert kofi.get(_url('vehicule', '1')).status_code == 404
        assert kofi.get(_url('logement', 'pas-un-uuid')).status_code == 404
        publiee = make_hebergement()  # déjà vérifiée : plus rien à faire
        assert kofi.get(_url('logement', publiee.id)).status_code == 404
        assert kofi.post(_url('logement', publiee.id, 'prendre')).status_code == 404


def test_dashboard_counts_free_mine_and_team(client_for, agents, annonce, piece):
    kofi, afi = (client_for(a) for a in agents)
    kofi.post(_url('logement', annonce.id, 'prendre'))
    par_type = {t['type']: t for t in afi.get(TABLEAU).data['types']}
    assert (par_type['logement']['libres'], par_type['logement']['miennes'], par_type['logement']['equipe']) == (0, 0, 1)
    assert (par_type['piece']['libres'], par_type['piece']['miennes'], par_type['piece']['equipe']) == (1, 0, 0)
    assert {t['type']: t['miennes'] for t in kofi.get(TABLEAU).data['types']}['logement'] == 1
