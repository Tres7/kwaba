"""Fixes from the security audit: attempt limits, audit log, invalid input, webhook, images."""
import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone
from rest_framework.test import APIClient

from apps.hebergements import views as hebergements_views
from apps.securite.models import JournalAuditModel
from apps.securite.permissions import EstAdministrateur

LOGIN = '/api/v1/auth/login/'
REGISTER = '/api/v1/auth/register/'
REFRESH = '/api/v1/auth/refresh/'
ME = '/api/v1/users/me/'
WEBHOOK = '/api/v1/paiements/webhooks/fedapay/'


def _actions(**filtres):
    return list(JournalAuditModel.objects.filter(**filtres).values_list('action', flat=True))


class TestConnexion:
    def test_eleventh_attempt_blocked_even_with_the_right_password(self, api_client, make_user, password):
        user = make_user()
        for _ in range(10):
            assert api_client.post(LOGIN, {'email': user.email, 'password': 'mauvais'}, format='json').status_code == 401
        response = api_client.post(LOGIN, {'email': user.email, 'password': password}, format='json')
        assert response.status_code == 429
        assert response.data['code'] == 'too_many_attempts'
        assert int(response['Retry-After']) > 0
        assert 'connexion_bloquee' in _actions(email=user.email)

    def test_success_resets_the_counter(self, api_client, make_user, password):
        user = make_user()
        for _ in range(9):
            api_client.post(LOGIN, {'email': user.email, 'password': 'mauvais'}, format='json')
        assert api_client.post(LOGIN, {'email': user.email, 'password': password}, format='json').status_code == 200
        for _ in range(9):
            api_client.post(LOGIN, {'email': user.email, 'password': 'mauvais'}, format='json')
        assert api_client.post(LOGIN, {'email': user.email, 'password': password}, format='json').status_code == 200

    def test_limit_is_per_address(self, api_client, make_user, password):
        cible, autre = make_user(), make_user()
        for _ in range(11):
            api_client.post(LOGIN, {'email': cible.email, 'password': 'mauvais'}, format='json')
        assert api_client.post(LOGIN, {'email': autre.email, 'password': password}, format='json').status_code == 200

    def test_attempts_are_audited_without_the_password(self, api_client, make_user, password):
        user = make_user()
        api_client.post(LOGIN, {'email': user.email, 'password': 'mauvais-secret'}, format='json')
        api_client.post(LOGIN, {'email': user.email, 'password': password}, format='json')
        assert _actions(utilisateur_id=user.id) == ['connexion', 'connexion_echec']
        assert 'mauvais-secret' not in json.dumps(list(JournalAuditModel.objects.values('details')))


class TestLimitesParIP:
    def _inscrire(self, client, n, **extra):
        return client.post(REGISTER, {
            'email': f'nouveau{n}@example.tg', 'first_name': 'Ama', 'last_name': 'Kossi',
            'password': 'Kwaba-Test-2026!', 'password_confirm': 'Kwaba-Test-2026!',
        }, format='json', **extra)

    def test_eleventh_registration_in_an_hour_is_throttled(self, api_client):
        statuts = [self._inscrire(api_client, n).status_code for n in range(11)]
        assert statuts == [201] * 10 + [429]

    def test_forged_forwarded_for_ignored_without_trusted_proxy(self, api_client):
        statuts = [self._inscrire(api_client, n, HTTP_X_FORWARDED_FOR=f'10.0.0.{n}').status_code for n in range(11)]
        assert statuts[-1] == 429

    def test_client_address_taken_from_the_trusted_proxy(self, api_client, settings):
        settings.NUM_PROXIES = 1
        # The proxy adds the real address last: what the client put before does not count
        for n in range(10):
            self._inscrire(api_client, n, HTTP_X_FORWARDED_FOR=f'1.2.3.{n}, 41.207.0.1')
        assert self._inscrire(api_client, 10, HTTP_X_FORWARDED_FOR='9.9.9.9, 41.207.0.1').status_code == 429
        assert self._inscrire(api_client, 11, HTTP_X_FORWARDED_FOR='41.207.0.2').status_code == 201


class TestAdministration:
    URL = '/admin/login/'

    def test_admin_login_locked_after_five_failures(self, make_user, password):
        admin = make_user(role='admin', is_staff=True, is_superuser=True)
        client = Client()
        for _ in range(5):
            assert client.post(self.URL, {'username': admin.email, 'password': 'mauvais'}).status_code == 200
        response = client.post(self.URL, {'username': admin.email, 'password': password})
        assert response.status_code == 429
        assert 'admin_connexion_echec' in _actions(email=admin.email)

    def test_admin_login_still_works(self, make_user, password):
        admin = make_user(role='admin', is_staff=True, is_superuser=True)
        response = Client().post(self.URL, {'username': admin.email, 'password': password, 'next': '/admin/'})
        assert response.status_code == 302

    def test_back_office_permission_reads_the_role_in_the_database(self, make_user, rf):
        permission = EstAdministrateur()
        for user, attendu in [
            (make_user(role='admin', is_staff=True), True),
            (make_user(role='admin'), True),
            (make_user(role='hote', is_staff=True), False),
            (make_user(), False),
        ]:
            requete = rf.get('/')
            requete.user = user
            assert permission.has_permission(requete, None) is attendu


class TestSessions:
    def test_deactivation_closes_the_sessions(self, api_client, make_user, password):
        user = make_user()
        jetons = api_client.post(LOGIN, {'email': user.email, 'password': password}, format='json').data
        session = APIClient()
        session.credentials(HTTP_AUTHORIZATION=f"Bearer {jetons['access']}")
        assert session.delete(ME).status_code == 204
        assert api_client.post(REFRESH, {'refresh': jetons['refresh']}, format='json').status_code == 401
        assert 'compte_desactive' in _actions(utilisateur_id=user.id)

    def test_jwt_not_signed_with_the_django_secret_key(self, settings):
        assert settings.SIMPLE_JWT['SIGNING_KEY'] != settings.SECRET_KEY


class TestProfil:
    @pytest.mark.parametrize('url', ['https://pixel-espion.example/moi.png', 'javascript:alert(1)', 'data:image/png;base64,AAAA'])
    def test_avatar_from_unknown_host_rejected(self, client_for, make_user, url):
        response = client_for(make_user()).patch(ME, {'avatar_url': url}, format='json')
        assert response.status_code == 400
        assert 'avatar_url' in response.data

    def test_google_avatar_accepted(self, client_for, make_user):
        url = 'https://lh3.googleusercontent.com/a/photo.jpg'
        assert client_for(make_user()).patch(ME, {'avatar_url': url}, format='json').status_code == 200

    def test_names_too_long_rejected_instead_of_500(self, client_for, make_user):
        response = client_for(make_user()).patch(ME, {'first_name': 'A' * 151}, format='json')
        assert response.status_code == 400

    def test_becoming_host_is_audited(self, client_for, make_user):
        user = make_user()
        client_for(user).patch(ME, {'role': 'hote'}, format='json')
        entree = JournalAuditModel.objects.get(action='role_modifie', utilisateur_id=user.id)
        assert entree.details == {'avant': 'voyageur', 'apres': 'hote'}


class TestEntreesInvalides:
    """A malformed id gives a 400 or 404 error, never a 500 error."""

    def test_transfers_filtered_by_malformed_reservation(self, raw_client, make_user):
        raw_client.force_authenticate(user=make_user())
        assert raw_client.get('/api/v1/transferts/?reservation=pas-un-uuid').status_code == 400

    def test_group_trip_with_malformed_ids(self, raw_client, make_user):
        user = make_user()
        raw_client.force_authenticate(user=user)
        voyage = raw_client.post('/api/v1/voyages/', {'nom': 'Lomé', 'destination': 'Lomé', 'nb_voyageurs': 2}, format='json').data
        base = f"/api/v1/voyages/{voyage['id']}"
        assert raw_client.post(f'{base}/propositions/', {'hebergement': 'x'}, format='json').status_code == 400
        assert raw_client.post(f'{base}/vote/', {'proposition': 'x'}, format='json').status_code == 400
        assert raw_client.post(f'{base}/retenir/', {'proposition': 'x'}, format='json').status_code == 400
        assert raw_client.post(f'{base}/reservations/', {'reservation': 'x'}, format='json').status_code == 400

    def test_listing_size_is_capped(self, api_client, make_hebergement, monkeypatch):
        monkeypatch.setattr(hebergements_views, 'MAX_RESULTATS', 3)
        hote = get_user_model().objects.create_user(email='hote@test.kwaba', password='x', role='hote')
        for _ in range(5):
            make_hebergement(host=hote)
        assert api_client.get('/api/v1/hebergements/?limit=1000').data['count'] == 3
        assert api_client.get('/api/v1/hebergements/').data['count'] == 3


class TestWebhook:
    def test_rejected_without_secret_outside_development(self, api_client, settings):
        settings.DEBUG = False
        settings.FEDAPAY = {**settings.FEDAPAY, 'WEBHOOK_SECRET': ''}
        response = api_client.post(WEBHOOK, json.dumps({'name': 'transaction.approved', 'entity': {'id': 1}}),
                                   content_type='application/json')
        assert response.status_code == 503
        assert 'webhook_refuse' in _actions()

    def test_bad_signature_audited(self, api_client, settings):
        settings.FEDAPAY = {**settings.FEDAPAY, 'WEBHOOK_SECRET': 'whsec_test'}
        response = api_client.post(WEBHOOK, '{}', content_type='application/json',
                                   HTTP_X_FEDAPAY_SIGNATURE=f't={int(timezone.now().timestamp())},s=faux')
        assert response.status_code == 400
        assert JournalAuditModel.objects.get(action='webhook_refuse').details == {'motif': 'signature_invalide'}


class TestConcierge:
    def test_conversation_creation_is_throttled(self, client_for, make_user):
        client = client_for(make_user())
        statuts = [client.post('/api/v1/concierge/conversations/').status_code for _ in range(31)]
        assert statuts == [201] * 30 + [429]
        assert client.get('/api/v1/concierge/conversations/').status_code == 200

    def test_quota_counter_is_exact(self, make_user, settings):
        from apps.concierge import services
        settings.CONCIERGE = {**settings.CONCIERGE, 'MAX_PAR_HEURE': 3, 'MAX_PAR_JOUR': 100}
        user = make_user()
        for _ in range(3):
            services.verifier_quota(user)
        with pytest.raises(services.ConciergeErreur):
            services.verifier_quota(user)


def test_audit_log_is_read_only_in_the_admin(make_user, password):
    admin = make_user(role='admin', is_staff=True, is_superuser=True)
    JournalAuditModel.objects.create(action='connexion', email='x@example.tg', cree_le=timezone.now() - timedelta(days=1))
    client = Client()
    client.force_login(admin)
    entree = JournalAuditModel.objects.get()
    assert client.get('/admin/securite/journalauditmodel/').status_code == 200
    assert client.post(f'/admin/securite/journalauditmodel/{entree.pk}/delete/', {'post': 'yes'}).status_code == 403
    assert JournalAuditModel.objects.exists()
