import pytest

from apps.users.infrastructure.persistence.models import UserModel, VerificationCode

REGISTER = '/api/v1/auth/register/'
VERIFY = '/api/v1/auth/verify/'
LOGIN = '/api/v1/auth/login/'


@pytest.fixture
def register(api_client, password):
    def _register(**overrides):
        payload = {
            'email': 'ama.kossi@example.tg',
            'first_name': 'Ama',
            'last_name': 'Kossi',
            'password': password,
            'password_confirm': password,
            **overrides,
        }
        return api_client.post(REGISTER, payload, format='json')

    return _register


def test_register_verify_then_login(api_client, register, password, code_envoye):
    response = register(phone='00228 90 00 00 00')

    assert response.status_code == 201
    assert 'password' not in response.data
    assert response.data['phone'] == '+22890000000'
    assert response.data['is_verified'] is False

    # Broker unavailable: the code is still sent by email (fallback)
    code = code_envoye('ama.kossi@example.tg')
    # The database only keeps the fingerprint of the code, never the code itself
    stocke = VerificationCode.objects.get(user__email='ama.kossi@example.tg').code
    assert code not in stocke and len(stocke) == 64

    response = api_client.post(VERIFY, {'email': 'ama.kossi@example.tg', 'code': code}, format='json')
    assert response.status_code == 200
    assert {'access', 'refresh'} <= response.data.keys()
    assert UserModel.objects.get(email='ama.kossi@example.tg').is_verified

    response = api_client.post(LOGIN, {'email': 'AMA.KOSSI@example.tg', 'password': password}, format='json')
    assert response.status_code == 200
    assert response.data['user']['email'] == 'ama.kossi@example.tg'


def test_email_already_taken_regardless_of_case(register, make_user):
    make_user(email='ama.kossi@example.tg')
    assert register(email='Ama.Kossi@Example.TG').status_code == 409


def test_admin_role_rejected_at_registration(register):
    response = register(role='admin')
    assert response.status_code == 400
    assert 'role' in response.data


def test_login_rejected_until_email_verified(api_client, make_user, password):
    user = make_user(is_verified=False)
    response = api_client.post(LOGIN, {'email': user.email, 'password': password}, format='json')
    assert response.status_code == 403
    assert response.data['code'] == 'unverified_email'


def test_wrong_password_and_unknown_email_get_same_response(api_client, make_user):
    user = make_user()
    wrong_password = api_client.post(LOGIN, {'email': user.email, 'password': 'faux'}, format='json')
    unknown_email = api_client.post(LOGIN, {'email': 'personne@example.tg', 'password': 'faux'}, format='json')
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.data == unknown_email.data
