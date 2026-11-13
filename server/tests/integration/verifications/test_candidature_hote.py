"""Becoming a host: a traveller opens a candidature, and only a listing validated by an agent gives the role."""
import json
from io import StringIO

import pytest
from django.core.management import call_command

from apps.contrats.models import PreinscriptionModel
from apps.hebergements.models import BrouillonAnnonceModel
from apps.activity.models import ActivityEntryModel
from apps.users.infrastructure.persistence.models import UserModel
from apps.verifications import services
from apps.verifications.models import PieceIdentiteModel

CANDIDATURE = '/api/v1/users/me/candidature/'
ME = '/api/v1/users/me/'
HEBERGEMENTS = '/api/v1/hebergements/'
BROUILLONS = '/api/v1/hebergements/brouillons/'
PHOTOS = '/api/v1/hebergements/photos/'
IDENTITE = '/api/v1/verifications/identite/'
VERSEMENT = '/api/v1/paiements/profil-versement/'
VISITES = '/api/v1/verifications/visites/'
ADMIN_USERS = '/api/v1/admin/users/'
TOUT_CONFORME = {'identite': True, 'adresse': True, 'photos': True, 'equipements': True}
ANNONCE = {
    'name': 'Villa des cocotiers', 'type': 'villa', 'city': 'Lomé', 'location': 'Bè Kpota', 'latitude': 6.13,
    'longitude': 1.22, 'price_per_night': 35000, 'max_guests': 4, 'amenities': ['wifi'], 'point_repere': 'Derrière la pharmacie', 'salles_de_bain': 1, 
    'chambres': 2, 'lits_doubles': 2, 'petit_dejeuner': 'inclus',
}


@pytest.fixture
def candidat(make_user):
    return make_user(phone='+22890000001', candidature_hote='ouverte')


@pytest.fixture
def agent(make_user):
    return make_user(role='agent')


@pytest.fixture
def admin(make_user):
    return make_user(role='admin')


def _identite_verifiee(utilisateur):
    PieceIdentiteModel.objects.create(hote_id=utilisateur.pk, type_piece='cni', statut='verifiee')


def _decider(client, hebergement, decision='validee', commentaire=''):
    return client.post(f'{VISITES}{hebergement.pk}/decision/', {
        'decision': decision, 'controles': json.dumps(TOUT_CONFORME), 'commentaire': commentaire,
    }, format='multipart')


class TestOuverture:
    def test_a_traveller_prepares_nothing_without_a_candidature(self, client_for, make_user):
        client = client_for(make_user(phone='+22890000001'))
        assert client.post(BROUILLONS, {'donnees': {}}, format='json').status_code == 403
        assert client.post(HEBERGEMENTS, ANNONCE, format='json').status_code == 403
        assert client.post(PHOTOS, {}, format='multipart').status_code == 403
        assert client.post(IDENTITE, {}, format='multipart').status_code == 403
        assert client.get(VERSEMENT).status_code == 403

    def test_opening_keeps_the_traveller_role_and_is_audited_once(self, client_for, make_user):
        utilisateur = make_user()
        client = client_for(utilisateur)
        reponse = client.post(CANDIDATURE)
        assert reponse.status_code == 200
        assert (reponse.data['role'], reponse.data['candidature_hote']) == ('voyageur', 'ouverte')

        assert client.post(CANDIDATURE).status_code == 200
        assert ActivityEntryModel.objects.filter(action='candidature_ouverte', actor_id=utilisateur.pk).count() == 1

    @pytest.mark.parametrize('role', ['hote', 'agent', 'admin'])
    def test_other_roles_are_left_alone(self, client_for, make_user, role):
        utilisateur = make_user(role=role)
        assert client_for(utilisateur).post(CANDIDATURE).data['candidature_hote'] == ''
        utilisateur.refresh_from_db()
        assert utilisateur.role == role

    def test_a_candidate_prepares_a_listing_and_stays_a_traveller(self, client_for, candidat):
        client = client_for(candidat)
        assert client.post(BROUILLONS, {'donnees': {'name': 'Villa'}}, format='json').status_code == 201
        assert client.get(VERSEMENT).status_code == 200
        assert client.post(HEBERGEMENTS, ANNONCE, format='json').status_code == 201
        assert client.get(ME).data['role'] == 'voyageur'

    def test_a_candidate_accepts_the_pre_registration_first(self, client_for, candidat, settings):
        settings.PRELANCEMENT = True
        reponse = client_for(candidat).post(HEBERGEMENTS, ANNONCE, format='json')
        assert (reponse.status_code, reponse.data['code']) == (403, 'preinscription_requise')


class TestValidation:
    def test_the_first_validated_listing_makes_a_host(self, client_for, candidat, agent, make_hebergement):
        annonce = make_hebergement(host=candidat, statut_verification='en_attente')
        _identite_verifiee(candidat)

        assert _decider(client_for(agent), annonce).status_code < 300

        candidat.refresh_from_db()
        assert (candidat.role, candidat.candidature_hote) == ('hote', '')
        entree = ActivityEntryModel.objects.get(action='role_modifie', target_kind='account', target_id=str(candidat.pk))
        assert (entree.details['avant'], entree.details['apres']) == ('voyageur', 'hote')

    def test_a_refused_listing_gives_no_role(self, client_for, candidat, agent, make_hebergement):
        annonce = make_hebergement(host=candidat, statut_verification='en_attente')
        _identite_verifiee(candidat)

        assert _decider(client_for(agent), annonce, 'refusee', 'Le logement ne correspond pas.').status_code < 300

        candidat.refresh_from_db()
        assert (candidat.role, candidat.candidature_hote) == ('voyageur', 'ouverte')


class TestRefus:
    def _refuser(self, client_for, admin, cible, motif='Dossier incohérent avec la pièce.'):
        return client_for(admin).patch(f'{ADMIN_USERS}{cible.pk}/', {'candidature': 'refusee', 'motif': motif}, format='json')

    def test_a_reason_is_required(self, client_for, admin, candidat):
        assert self._refuser(client_for, admin, candidat, motif='Non').status_code == 400

    def test_refused_candidate_is_blocked_and_sees_the_reason(self, client_for, admin, candidat):
        assert self._refuser(client_for, admin, candidat).status_code == 200

        candidat.refresh_from_db()
        client = client_for(candidat)
        moi = client.get(ME).data
        assert (moi['candidature_hote'], moi['candidature_motif']) == ('refusee', 'Dossier incohérent avec la pièce.')
        assert client.post(HEBERGEMENTS, ANNONCE, format='json').status_code == 403
        reponse = client.post(CANDIDATURE)
        assert (reponse.status_code, reponse.data['code']) == (403, 'candidature_refusee')

    def test_refused_candidate_gets_no_visit_and_no_validation(
            self, client_for, admin, agent, candidat, make_hebergement):
        annonce = make_hebergement(host=candidat, statut_verification='en_attente')
        _identite_verifiee(candidat)
        self._refuser(client_for, admin, candidat)

        assert services.annonces_a_visiter() == []
        assert _decider(client_for(agent), annonce).status_code >= 400
        candidat.refresh_from_db()
        assert candidat.role == 'voyageur'

    def test_the_team_can_reopen_a_refused_candidature(self, client_for, admin, candidat):
        self._refuser(client_for, admin, candidat)
        reponse = client_for(admin).patch(f'{ADMIN_USERS}{candidat.pk}/', {'candidature': 'ouverte'}, format='json')
        assert (reponse.status_code, reponse.data['candidature_hote']) == (200, 'ouverte')

    def test_only_an_open_candidature_can_be_refused(self, client_for, admin, make_user):
        assert self._refuser(client_for, admin, make_user()).status_code == 400

    def test_the_team_sets_the_commission_of_a_candidate(self, client_for, admin, candidat):
        reponse = client_for(admin).patch(
            f'{ADMIN_USERS}{candidat.pk}/', {'conditions': {'categorie': 'hotel'}}, format='json')
        assert (reponse.status_code, reponse.data['conditions']['categorie']) == (200, 'hotel')


class TestMigrationDesHotes:
    @pytest.fixture
    def hotes(self, make_user, make_hebergement):
        valide = make_user(role='hote')
        make_hebergement(host=valide, statut_verification='verifiee')
        en_attente = make_user(role='hote')
        make_hebergement(host=en_attente, statut_verification='en_attente')
        brouillon = make_user(role='hote')
        BrouillonAnnonceModel.objects.create(host_id=brouillon.pk)
        preinscrit = make_user(role='hote')
        PreinscriptionModel.objects.create(hote_id=preinscrit.pk, version=1, langue='fr', empreinte_texte='x')
        piece = make_user(role='hote')
        PieceIdentiteModel.objects.create(hote_id=piece.pk, type_piece='cni', statut='soumise')
        rien = make_user(role='hote')
        return valide, en_attente, brouillon, preinscrit, piece, rien

    def test_simulation_by_default(self, hotes):
        sortie = StringIO()
        call_command('migrer_hotes', stdout=sortie)
        assert '1 hôte(s) gardé(s), 4 candidat(s), 1 repassé(s) voyageur' in sortie.getvalue()
        assert UserModel.objects.filter(role='hote').count() == 6

    def test_applying_the_rule(self, hotes):
        valide, en_attente, brouillon, preinscrit, piece, rien = hotes
        call_command('migrer_hotes', '--appliquer', stdout=StringIO())

        for utilisateur in hotes:
            utilisateur.refresh_from_db()
        assert valide.role == 'hote'
        for commence in (en_attente, brouillon, preinscrit, piece):
            assert (commence.role, commence.candidature_hote) == ('voyageur', 'ouverte')
        assert (rien.role, rien.candidature_hote) == ('voyageur', '')
        assert ActivityEntryModel.objects.filter(action='role_modifie').count() == 5
        assert ActivityEntryModel.objects.filter(action='roles_hotes_migres').count() == 1

    def test_applying_twice_changes_nothing_more(self, hotes):
        call_command('migrer_hotes', '--appliquer', stdout=StringIO())
        call_command('migrer_hotes', '--appliquer', stdout=StringIO())
        assert ActivityEntryModel.objects.filter(action='role_modifie').count() == 5


class TestBackOffice:
    def test_candidates_found_by_status(self, client_for, admin, candidat, make_user):
        refuse = make_user(candidature_hote='refusee')
        make_user()
        client = client_for(admin)

        ouvertes = client.get(ADMIN_USERS, {'candidature': 'ouverte'}).data['results']
        refusees = client.get(ADMIN_USERS, {'candidature': 'refusee'}).data['results']

        assert [u['id'] for u in ouvertes] == [str(candidat.pk)]
        assert [u['id'] for u in refusees] == [str(refuse.pk)]

    def test_unknown_filter_ignored(self, client_for, admin, candidat):
        assert client_for(admin).get(ADMIN_USERS, {'candidature': 'x'}).status_code == 200


class TestStatutAnnonce:
    MES_ANNONCES = '/api/v1/hebergements/mine/'

    def _statut(self, client_for, hote):
        return client_for(hote).get(self.MES_ANNONCES).data['results'][0]['statut_annonce']

    @pytest.mark.parametrize(('champs', 'attendu'), [
        ({'statut_verification': 'en_attente'}, 'en_verification'),
        ({'statut_verification': 'refusee'}, 'refusee'),
        ({'statut_verification': 'verifiee'}, 'publiee'),
        ({'statut_verification': 'verifiee', 'is_available': False}, 'masquee'),
    ])
    def test_for_each_state(self, client_for, make_user, make_hebergement, champs, attendu):
        hote = make_user(role='hote')
        make_hebergement(host=hote, **champs)
        assert self._statut(client_for, hote) == attendu

    def test_validated_but_waiting_for_the_opening(self, client_for, make_user, make_hebergement, settings):
        settings.PRELANCEMENT = True
        hote = make_user(role='hote')
        make_hebergement(host=hote)
        assert self._statut(client_for, hote) == 'validee'

    def test_never_shown_to_travellers(self, api_client, make_hebergement):
        annonce = make_hebergement()
        assert api_client.get(f'{HEBERGEMENTS}{annonce.pk}/').data['statut_annonce'] is None
