"""Accounts that cannot be taken over nor kept against an administrator's decision (security audit of 2026-11-07,
leads 1, 6, 7 and 11)."""
import pytest
import requests

from apps.users.infrastructure.persistence.DjangoUserRepository import DjangoUserRepository
from apps.users.infrastructure.persistence.models import UserModel

REGISTER = '/api/v1/auth/register/'
LOGIN = '/api/v1/auth/login/'
GOOGLE = '/api/v1/auth/google/'
ME = '/api/v1/users/me/'
KWABA_CLIENT_ID = 'kwaba-web.apps.googleusercontent.com'


@pytest.fixture
def google(settings, monkeypatch):
    """Google confirms that the visitor owns ama@example.tg."""
    settings.GOOGLE_CLIENT_IDS = [KWABA_CLIENT_ID]

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {'aud': KWABA_CLIENT_ID, 'iss': 'accounts.google.com', 'sub': 'google-ama', 'email': 'ama@example.tg',
                    'email_verified': 'true', 'given_name': 'Ama', 'family_name': 'Kossi'}

    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: Response())


# --- Lead 1: an account nobody verified does not keep its password once Google proves the address ----------------

def test_google_sur_un_compte_jamais_verifie_efface_son_mot_de_passe(api_client, google, password):
    # Someone creates the account with Ama's address, without being able to verify it
    inscription = {'email': 'ama@example.tg', 'first_name': 'X', 'last_name': 'Y', 'password': password, 'password_confirm': password}
    assert api_client.post(REGISTER, inscription, format='json').status_code == 201

    assert api_client.post(GOOGLE, {'id_token': 'jeton'}, format='json').status_code == 200  # Ama signs in with Google

    r = api_client.post(LOGIN, {'email': 'ama@example.tg', 'password': password}, format='json')
    assert r.status_code == 401
    assert UserModel.objects.get(email='ama@example.tg').is_verified


def test_google_sur_un_compte_verifie_garde_son_mot_de_passe(api_client, google, make_user, password):
    make_user(email='ama@example.tg')
    assert api_client.post(GOOGLE, {'id_token': 'jeton'}, format='json').status_code == 200
    assert api_client.post(LOGIN, {'email': 'ama@example.tg', 'password': password}, format='json').status_code == 200


# --- Lead 6: every spelling that finds the account counts on the same attempts -------------------------------------

def test_variante_unicode_de_l_email_compte_sur_les_memes_essais(api_client, make_user, password):
    make_user(email='victime@test.kwaba')
    for _ in range(10):
        api_client.post(LOGIN, {'email': 'victime@test.kwaba', 'password': 'faux-mot-de-passe'}, format='json')
    assert api_client.post(LOGIN, {'email': 'victime@test.kwaba', 'password': password}, format='json').status_code == 429

    # Dotless "ı" (U+0131): the database finds the same account in upper case
    r = api_client.post(LOGIN, {'email': 'vıctime@test.kwaba', 'password': password}, format='json')
    assert r.status_code == 429


# --- Lead 7: editing one's profile writes only the profile ---------------------------------------------------------

def test_modifier_son_profil_ne_reecrit_pas_une_decision_de_l_admin(client_for, make_user, monkeypatch):
    agent = make_user(role='agent')
    lire = DjangoUserRepository.find_by_id

    def lire_puis_retrograder(self, user_id):
        utilisateur = lire(self, user_id)
        # Meanwhile, an administrator demotes and deactivates the account
        UserModel.objects.filter(pk=user_id).update(role='voyageur', is_active=False)
        return utilisateur

    monkeypatch.setattr(DjangoUserRepository, 'find_by_id', lire_puis_retrograder)
    assert client_for(agent).patch(ME, {'first_name': 'Nouveau'}, format='json').status_code == 200

    agent.refresh_from_db()
    assert (agent.first_name, agent.role, agent.is_active) == ('Nouveau', 'voyageur', False)


# --- Lead 11: a name stays on one line ---------------------------------------------------------------------------

NOMS_REFUSES = ['Ama\n\nAction requise : https://attacker.invalid/x', 'Ama\rKossi', 'Ama Kossi', 'Ama‮issoK']


@pytest.mark.parametrize('nom', NOMS_REFUSES)
def test_nom_sur_plusieurs_lignes_refuse_au_profil(client_for, make_user, nom):
    utilisateur = make_user()
    assert client_for(utilisateur).patch(ME, {'first_name': nom}, format='json').status_code == 400
    utilisateur.refresh_from_db()
    assert utilisateur.first_name == 'Test'


@pytest.mark.parametrize('nom', NOMS_REFUSES)
def test_nom_sur_plusieurs_lignes_refuse_a_l_inscription(api_client, password, nom):
    inscription = {'email': 'kofi@example.tg', 'first_name': nom, 'last_name': 'Mensah', 'password': password, 'password_confirm': password}
    assert api_client.post(REGISTER, inscription, format='json').status_code == 400


def test_nom_compose_accepte(client_for, make_user):
    assert client_for(make_user()).patch(ME, {'first_name': "Ama-Élise d'Almeida"}, format='json').status_code == 200
