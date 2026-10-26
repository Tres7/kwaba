from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.core import mail
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.securite.models import JournalAuditModel
from apps.users.infrastructure.persistence.models import VerificationCode, hacher_code

VERIFY = '/api/v1/auth/verify/'
RESEND = '/api/v1/auth/resend-code/'
RESET = '/api/v1/auth/password-reset/'
RESET_CONFIRM = '/api/v1/auth/password-reset/confirm/'
LOGIN = '/api/v1/auth/login/'
REFRESH = '/api/v1/auth/refresh/'
ME = '/api/v1/users/me/'
NEW_PASSWORD = 'Nouveau-Mot-De-Passe-2026!'


# The generator produces 100000 to 999999: a new code can never be equal to this one
INITIAL_CODE = '012345'


@pytest.fixture
def unverified(make_user):
    user = make_user(is_verified=False)
    VerificationCode.objects.create(
        user=user, code=hacher_code(user.id, INITIAL_CODE), expires_at=timezone.now() + timedelta(minutes=10),
    )
    return user


def _age_codes(user, seconds):
    """Pretends the last code was sent `seconds` seconds ago."""
    VerificationCode.objects.filter(user=user).update(
        expires_at=timezone.now() + timedelta(minutes=10) - timedelta(seconds=seconds),
    )


def _verify(client, user, code):
    return client.post(VERIFY, {'email': user.email, 'code': code}, format='json')


class TestVerify:
    def test_wrong_code(self, api_client, unverified):
        response = _verify(api_client, unverified, '000000')
        assert response.status_code == 400
        assert response.data['code'] == 'invalid_code'

    def test_code_stored_as_hash_only(self, unverified):
        stocke = VerificationCode.objects.get(user=unverified).code
        assert stocke != INITIAL_CODE and len(stocke) == 64

    def test_five_failures_invalidate_the_code(self, api_client, unverified):
        for _ in range(5):
            _verify(api_client, unverified, '000000')
        # Even the right code no longer works: a new one has to be asked for
        assert _verify(api_client, unverified, INITIAL_CODE).status_code == 400
        assert not VerificationCode.objects.filter(user=unverified).exists()
        assert JournalAuditModel.objects.filter(action='code_bloque', utilisateur_id=unverified.id).exists()

    def test_expired_code(self, api_client, unverified):
        _age_codes(unverified, seconds=11 * 60)
        assert _verify(api_client, unverified, INITIAL_CODE).status_code == 400

    def test_already_verified(self, api_client, make_user):
        user = make_user()
        response = _verify(api_client, user, INITIAL_CODE)
        assert response.data['code'] == 'already_verified'

    def test_unknown_email_same_answer_as_wrong_code(self, api_client):
        response = api_client.post(VERIFY, {'email': 'personne@example.tg', 'code': '123456'}, format='json')
        assert response.status_code == 400
        assert response.data['code'] == 'invalid_code'

    def test_success_sends_welcome_email(self, api_client, unverified):
        response = _verify(api_client, unverified, INITIAL_CODE)
        assert response.status_code == 200
        assert [m.to for m in mail.outbox] == [[unverified.email]]

    def test_missing_fields(self, api_client):
        assert api_client.post(VERIFY, {}, format='json').status_code == 400


class TestResendCode:
    def test_cooldown_before_60_seconds(self, api_client, unverified):
        _age_codes(unverified, seconds=30)
        response = api_client.post(RESEND, {'email': unverified.email}, format='json')
        assert response.status_code == 429
        assert 0 < response.data['retry_after'] <= 31

    def test_new_code_after_60_seconds_invalidates_old_one(self, api_client, unverified, code_envoye):
        _age_codes(unverified, seconds=61)
        assert api_client.post(RESEND, {'email': unverified.email}, format='json').status_code == 200

        code = code_envoye(unverified.email)
        assert _verify(api_client, unverified, INITIAL_CODE).status_code == 400
        assert _verify(api_client, unverified, code).status_code == 200

    def test_resend_does_not_give_new_attempts(self, api_client, unverified, code_envoye):
        """Asking for a new code does not reset the counter: 10 attempts per hour and per address in total."""
        for _ in range(5):
            _verify(api_client, unverified, '000000')
        _age_codes(unverified, seconds=61)
        api_client.post(RESEND, {'email': unverified.email}, format='json')
        for _ in range(5):
            _verify(api_client, unverified, '000000')
        _age_codes(unverified, seconds=61)
        api_client.post(RESEND, {'email': unverified.email}, format='json')

        response = _verify(api_client, unverified, code_envoye(unverified.email))
        assert response.status_code == 429
        assert response['Retry-After']

    def test_a_few_mistakes_then_the_right_code(self, api_client, unverified, code_envoye):
        for _ in range(3):
            _verify(api_client, unverified, '000000')
        assert _verify(api_client, unverified, INITIAL_CODE).status_code == 200

    def test_unknown_email_same_answer_as_success(self, api_client):
        response = api_client.post(RESEND, {'email': 'personne@example.tg'}, format='json')
        assert response.status_code == 200

    def test_already_verified(self, api_client, make_user):
        assert api_client.post(RESEND, {'email': make_user().email}, format='json').status_code == 400


class TestPasswordReset:
    def test_same_response_for_existing_unknown_and_inactive_accounts(self, api_client, make_user):
        responses = [
            api_client.post(RESET, {'email': email}, format='json')
            for email in (make_user().email, 'personne@example.tg', make_user(is_active=False).email)
        ]
        assert {r.status_code for r in responses} == {200}
        assert responses[0].data == responses[1].data == responses[2].data
        assert len(mail.outbox) == 1

    def test_second_request_within_cooldown_sends_no_email(self, api_client, make_user):
        user = make_user()
        first = api_client.post(RESET, {'email': user.email}, format='json')
        second = api_client.post(RESET, {'email': user.email}, format='json')
        assert first.data == second.data
        assert len(mail.outbox) == 1

    def test_full_reset_flow(self, api_client, make_user, password, code_envoye):
        user = make_user(is_verified=False)
        api_client.post(RESET, {'email': user.email}, format='json')
        code = code_envoye(user.email)

        response = api_client.post(RESET_CONFIRM, {
            'email': user.email, 'code': code, 'password': NEW_PASSWORD, 'password_confirm': NEW_PASSWORD,
        }, format='json')

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_verified is True
        assert not VerificationCode.objects.filter(user=user).exists()
        assert api_client.post(LOGIN, {'email': user.email, 'password': NEW_PASSWORD}, format='json').status_code == 200
        assert api_client.post(LOGIN, {'email': user.email, 'password': password}, format='json').status_code == 401
        assert JournalAuditModel.objects.filter(action='mdp_reinitialise', utilisateur_id=user.id).exists()

    def test_reset_closes_every_open_session(self, api_client, make_user, password, code_envoye):
        """After a reset, neither the access tokens nor the refresh tokens issued before work anymore."""
        user = make_user()
        jetons = api_client.post(LOGIN, {'email': user.email, 'password': password}, format='json').data
        session = APIClient()
        session.credentials(HTTP_AUTHORIZATION=f"Bearer {jetons['access']}")
        assert session.get(ME).status_code == 200

        api_client.post(RESET, {'email': user.email}, format='json')
        api_client.post(RESET_CONFIRM, {
            'email': user.email, 'code': code_envoye(user.email), 'password': NEW_PASSWORD,
            'password_confirm': NEW_PASSWORD,
        }, format='json')

        assert session.get(ME).status_code == 401
        assert api_client.post(REFRESH, {'refresh': jetons['refresh']}, format='json').status_code == 401

    @pytest.mark.parametrize('code', ['abcdef', '000000'])
    def test_wrong_code(self, api_client, make_user, code):
        user = make_user()
        api_client.post(RESET, {'email': user.email}, format='json')
        response = api_client.post(RESET_CONFIRM, {
            'email': user.email, 'code': code, 'password': NEW_PASSWORD, 'password_confirm': NEW_PASSWORD,
        }, format='json')
        assert response.status_code == 400

    def test_five_failures_invalidate_the_code_ten_lock_the_address(self, api_client, make_user, code_envoye):
        user = make_user()
        api_client.post(RESET, {'email': user.email}, format='json')
        code = code_envoye(user.email)
        payload = {'email': user.email, 'code': '000000', 'password': NEW_PASSWORD, 'password_confirm': NEW_PASSWORD}
        for _ in range(5):
            api_client.post(RESET_CONFIRM, payload, format='json')
        assert api_client.post(RESET_CONFIRM, {**payload, 'code': code}, format='json').status_code == 400
        for _ in range(4):
            api_client.post(RESET_CONFIRM, payload, format='json')
        assert api_client.post(RESET_CONFIRM, payload, format='json').status_code == 429

    def test_weak_password_rejected(self, api_client, make_user, code_envoye):
        user = make_user()
        api_client.post(RESET, {'email': user.email}, format='json')
        response = api_client.post(RESET_CONFIRM, {
            'email': user.email, 'code': code_envoye(user.email), 'password': '12345678', 'password_confirm': '12345678',
        }, format='json')
        assert response.status_code == 400


@pytest.mark.django_db(transaction=True)
def test_simultaneous_guesses_cannot_exceed_the_limit(make_user):
    """Attempts sent in parallel (one database connection each) do not get around the limit."""
    user = make_user(is_verified=False)
    VerificationCode.objects.create(
        user=user, code=hacher_code(user.id, INITIAL_CODE), expires_at=timezone.now() + timedelta(minutes=10),
    )

    def essai(_):
        try:
            return APIClient().post(VERIFY, {'email': user.email, 'code': '000000'}, format='json').status_code
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuts = list(pool.map(essai, range(30)))

    assert statuts.count(400) == 10
    assert statuts.count(429) == 20
