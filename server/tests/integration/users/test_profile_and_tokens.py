import threading

import pytest
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

ME = '/api/v1/users/me/'
LOGIN = '/api/v1/auth/login/'
REFRESH = '/api/v1/auth/refresh/'
LOGOUT = '/api/v1/auth/logout/'


def _login(api_client, user, password):
    return api_client.post(LOGIN, {'email': user.email, 'password': password}, format='json').data


class TestMe:
    def test_requires_authentication(self, api_client):
        assert api_client.get(ME).status_code == 401

    def test_update_names_and_ignore_empty_fields(self, client_for, make_user):
        user = make_user(first_name='Ama', last_name='Kossi')
        response = client_for(user).patch(ME, {'first_name': 'Afi', 'last_name': '  '}, format='json')
        assert response.status_code == 200
        assert (response.data['first_name'], response.data['last_name']) == ('Afi', 'Kossi')

    def test_invalid_phone(self, client_for, make_user):
        assert client_for(make_user()).patch(ME, {'phone': '1234'}, format='json').status_code == 400

    def test_phone_of_another_account(self, client_for, make_user):
        make_user(phone='+22890000000')
        assert client_for(make_user()).patch(ME, {'phone': '+228 90 00 00 00'}, format='json').status_code == 400

    def test_become_host_but_never_admin(self, client_for, make_user):
        user = make_user()
        client = client_for(user)
        assert client.patch(ME, {'role': 'admin'}, format='json').data['role'] == 'voyageur'
        assert client.patch(ME, {'role': 'hote'}, format='json').data['role'] == 'hote'

    def test_delete_deactivates_account(self, api_client, make_user, password):
        user = make_user()
        access = _login(api_client, user, password)['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        assert api_client.delete(ME).status_code == 204
        assert api_client.get(ME).status_code == 401
        api_client.credentials()
        response = api_client.post(LOGIN, {'email': user.email, 'password': password}, format='json')
        assert response.data['code'] == 'inactive'


class TestRefresh:
    def test_refresh_returns_new_tokens(self, api_client, make_user, password):
        tokens = _login(api_client, make_user(), password)
        response = api_client.post(REFRESH, {'refresh': tokens['refresh']}, format='json')
        assert response.status_code == 200
        assert {'access', 'refresh'} <= response.data.keys()

    def test_invalid_refresh(self, api_client):
        assert api_client.post(REFRESH, {'refresh': 'pas-un-jeton'}, format='json').status_code == 401

    def test_refresh_token_is_rotated(self, api_client, make_user, password):
        refresh = _login(api_client, make_user(), password)['refresh']
        assert api_client.post(REFRESH, {'refresh': refresh}, format='json').data['refresh'] != refresh

    def test_reuse_within_grace_period_returns_the_same_pair(self, api_client, make_user, password):
        # NextAuth renews the same token in parallel when a page loads: no call must fail
        refresh = _login(api_client, make_user(), password)['refresh']
        first = api_client.post(REFRESH, {'refresh': refresh}, format='json')
        second = api_client.post(REFRESH, {'refresh': refresh}, format='json')
        assert second.status_code == 200
        assert second.data == first.data

    def test_rotated_refresh_token_rejected_after_grace_period(self, api_client, make_user, password, settings):
        settings.JWT_REFRESH_GRACE_SECONDS = 0  # delay elapsed
        refresh = _login(api_client, make_user(), password)['refresh']
        new_refresh = api_client.post(REFRESH, {'refresh': refresh}, format='json').data['refresh']

        assert api_client.post(REFRESH, {'refresh': refresh}, format='json').status_code == 401
        assert api_client.post(REFRESH, {'refresh': new_refresh}, format='json').status_code == 200


class TestLogout:
    def test_refresh_token_refused_after_signing_out(self, api_client, make_user, password):
        # No access token: it may already have expired when the user signs out
        refresh = _login(api_client, make_user(), password)['refresh']
        assert api_client.post(LOGOUT, {'refresh': refresh}, format='json').status_code == 200
        assert api_client.post(REFRESH, {'refresh': refresh}, format='json').status_code == 401

    def test_other_sessions_stay_open(self, api_client, make_user, password):
        user = make_user()
        ici, ailleurs = _login(api_client, user, password), _login(api_client, user, password)
        api_client.post(LOGOUT, {'refresh': ici['refresh']}, format='json')
        assert api_client.post(REFRESH, {'refresh': ailleurs['refresh']}, format='json').status_code == 200

    def test_old_token_cannot_reopen_the_session_during_the_grace_period(self, api_client, make_user, password):
        refresh = _login(api_client, make_user(), password)['refresh']
        new_refresh = api_client.post(REFRESH, {'refresh': refresh}, format='json').data['refresh']
        api_client.post(LOGOUT, {'refresh': new_refresh}, format='json')
        assert api_client.post(REFRESH, {'refresh': refresh}, format='json').status_code == 401

    def test_invalid_token_refused(self, api_client):
        assert api_client.post(LOGOUT, {'refresh': 'pas-un-jeton'}, format='json').status_code == 401


@pytest.mark.django_db(transaction=True)
def test_simultaneous_refreshes_of_the_same_token_all_succeed(make_user, password, monkeypatch):
    refresh = _login(APIClient(), make_user(), password)['refresh']

    # Forces both calls to enter the rotation together: without the lock, each would produce
    # its own pair (and one of them would see the token already blacklisted)
    barrier = threading.Barrier(2, timeout=3)
    original = TokenRefreshSerializer.validate

    def wait_then_rotate(self, attrs):
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            pass
        return original(self, attrs)

    monkeypatch.setattr(TokenRefreshSerializer, 'validate', wait_then_rotate)
    responses = []

    def renew():
        try:
            responses.append(APIClient().post(REFRESH, {'refresh': refresh}, format='json'))
        finally:
            connection.close()

    threads = [threading.Thread(target=renew) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].data['refresh'] == responses[1].data['refresh']
