from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.urls import URLResolver, get_resolver
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.securite.models import JournalAuditModel
from apps.securite.permissions import ROUTES_TOUS_ADMINS, SECTIONS_ADMIN, section_de
from apps.users.infrastructure.persistence.models import UserModel

ADMIN = '/api/v1/admin/'


def _user_url(compte):
    return f'{ADMIN}users/{compte.pk}/'


def _client_jwt(compte):
    """Real token, unlike client_for (force_authenticate): the end date is checked by the authentication itself."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {AccessToken.for_user(compte)}')
    return client


@pytest.fixture
def super_admin(make_user):
    return make_user(role='admin', is_superuser=True, is_staff=True)


@pytest.fixture
def api_super(super_admin, client_for):
    return client_for(super_admin)


@pytest.fixture
def admin(make_user):
    return make_user(role='admin')


@pytest.fixture
def api_admin(admin, client_for):
    return client_for(admin)


class TestPlainAdminLimits:
    def test_cannot_change_another_admin(self, api_admin, make_user):
        autre = make_user(role='admin')
        for patch in ({'role': 'voyageur'}, {'is_active': False}):
            assert api_admin.patch(_user_url(autre), patch, format='json').status_code == 403
        autre.refresh_from_db()
        assert autre.role == 'admin' and autre.is_active

    def test_cannot_change_a_super_admin(self, api_admin, super_admin):
        assert api_admin.patch(_user_url(super_admin), {'is_active': False}, format='json').status_code == 403
        super_admin.refresh_from_db()
        assert super_admin.is_active

    def test_cannot_make_someone_admin(self, api_admin, make_user):
        voyageur = make_user(role='voyageur')
        assert api_admin.patch(_user_url(voyageur), {'role': 'admin'}, format='json').status_code == 403
        voyageur.refresh_from_db()
        assert voyageur.role == 'voyageur'

    def test_cannot_set_admin_limits(self, api_admin, make_user):
        autre = make_user(role='admin')
        assert api_admin.patch(_user_url(autre), {'admin_sections': ['avis']}, format='json').status_code == 403

    def test_still_manages_other_accounts(self, api_admin, make_user):
        voyageur = make_user(role='voyageur')
        assert api_admin.patch(_user_url(voyageur), {'role': 'agent'}, format='json').status_code == 200
        assert api_admin.patch(_user_url(voyageur), {'is_active': False}, format='json').status_code == 200

    def test_super_admin_flag_cannot_be_sent(self, api_super, make_user):
        autre = make_user(role='admin')
        api_super.patch(_user_url(autre), {'is_superuser': True, 'est_super_admin': True}, format='json')
        autre.refresh_from_db()
        assert not autre.is_superuser


class TestSuperAdmin:
    def test_grants_and_removes_admin(self, api_super, make_user):
        hote = make_user(role='hote')
        assert api_super.patch(_user_url(hote), {'role': 'admin'}, format='json').status_code == 200
        hote.refresh_from_db()
        assert (hote.role, hote.role_avant_admin) == ('admin', 'hote')

        assert api_super.patch(_user_url(hote), {'role': 'hote'}, format='json').status_code == 200
        hote.refresh_from_db()
        assert (hote.role, hote.role_avant_admin, hote.admin_sections) == ('hote', '', None)

    def test_deactivates_an_admin(self, api_super, make_user):
        autre = make_user(role='admin')
        assert api_super.patch(_user_url(autre), {'is_active': False}, format='json').status_code == 200

    def test_cannot_change_the_other_super_admin(self, api_super, make_user):
        autre = make_user(role='admin', is_superuser=True)
        for patch in ({'role': 'voyageur'}, {'is_active': False}, {'admin_sections': ['avis']}):
            assert api_super.patch(_user_url(autre), patch, format='json').status_code == 403

    def test_sets_limits_and_end_date(self, api_super, make_user):
        autre = make_user(role='admin')
        fin = timezone.now() + timedelta(days=7)
        reponse = api_super.patch(_user_url(autre), {'admin_sections': ['avis', 'finances'], 'admin_expire_le': fin.isoformat()},
                                  format='json')
        assert reponse.status_code == 200
        assert reponse.data['admin_sections'] == ['avis', 'finances']
        autre.refresh_from_db()
        assert autre.admin_expire_le == fin
        assert JournalAuditModel.objects.filter(action='droits_admin_modifies').exists()

    def test_creates_a_temporary_admin_in_one_request(self, api_super, make_user):
        voyageur = make_user(role='voyageur')
        fin = (timezone.now() + timedelta(days=1)).isoformat()
        reponse = api_super.patch(_user_url(voyageur), {'role': 'admin', 'admin_expire_le': fin}, format='json')
        assert reponse.status_code == 200
        voyageur.refresh_from_db()
        assert voyageur.role == 'admin' and voyageur.admin_expire_le

    @pytest.mark.parametrize('champs', [
        {'admin_sections': ['inconnue']}, {'admin_sections': []}, {'admin_sections': 'avis'},
        {'admin_expire_le': '2020-01-01T00:00:00+00:00'}, {'admin_expire_le': 'demain'}, {'admin_expire_le': '2099-01-01T00:00:00'},
    ])
    def test_refuses_invalid_limits(self, api_super, make_user, champs):
        assert api_super.patch(_user_url(make_user(role='admin')), champs, format='json').status_code == 400

    def test_limits_only_apply_to_admins(self, api_super, make_user):
        reponse = api_super.patch(_user_url(make_user(role='hote')), {'admin_sections': ['avis']}, format='json')
        assert reponse.status_code == 400


class TestSections:
    def test_limited_admin_only_reaches_their_sections(self, make_user, client_for):
        api = client_for(make_user(role='admin', admin_sections=['avis']))
        assert api.get(ADMIN + 'avis/').status_code == 200
        for route in ('users/', 'reservations/', 'stats/', 'paiements/tarifs/', 'contrats/'):
            assert api.get(ADMIN + route).status_code == 403

    def test_finances_and_rates_are_separate(self, make_user, client_for):
        api = client_for(make_user(role='admin', admin_sections=['tarifs']))
        assert api.get(ADMIN + 'paiements/tarifs/').status_code == 200
        assert api.get(ADMIN + 'paiements/finances/').status_code == 403

    def test_verifications_section_covers_the_agent_space(self, make_user, client_for):
        assert client_for(make_user(role='admin', admin_sections=['avis'])).get('/api/v1/verifications/compteurs/').status_code == 403
        assert client_for(make_user(role='admin', admin_sections=['verifications'])).get('/api/v1/verifications/compteurs/').status_code == 200
        assert client_for(make_user(role='agent')).get('/api/v1/verifications/compteurs/').status_code == 200

    def test_admin_without_limits_and_super_admin_see_everything(self, api_admin, make_user, client_for):
        assert api_admin.get(ADMIN + 'stats/').status_code == 200
        api = client_for(make_user(role='admin', is_superuser=True, admin_sections=['avis']))
        assert api.get(ADMIN + 'stats/').status_code == 200

    def test_rights_endpoint(self, make_user, client_for, api_super):
        droits = client_for(make_user(role='admin', admin_sections=['avis'])).get(ADMIN + 'droits/').data
        assert (droits['est_super_admin'], droits['sections']) == (False, ['avis'])
        droits = api_super.get(ADMIN + 'droits/').data
        assert droits['est_super_admin'] and droits['sections'] == list(SECTIONS_ADMIN)

    def test_every_admin_route_belongs_to_a_section(self):
        def routes(motifs, prefixe=''):
            for motif in motifs:
                chemin = prefixe + str(motif.pattern)
                if isinstance(motif, URLResolver):
                    yield from routes(motif.url_patterns, chemin)
                else:
                    yield '/' + chemin

        admin = [r for r in routes(get_resolver().url_patterns) if r.startswith(ADMIN)]
        assert admin
        orphelines = [r for r in admin if section_de(r) is None and not r.removeprefix(ADMIN).startswith(ROUTES_TOUS_ADMINS)]
        assert orphelines == []


class TestTemporaryAdmin:
    def test_loses_rights_at_the_first_request_after_the_date(self, make_user):
        hote = make_user(role='admin', role_avant_admin='hote', admin_sections=['avis'],
                         admin_expire_le=timezone.now() - timedelta(minutes=1))
        assert _client_jwt(hote).get(ADMIN + 'avis/').status_code == 403
        hote.refresh_from_db()
        assert (hote.role, hote.admin_sections, hote.admin_expire_le, hote.role_avant_admin) == ('hote', None, None, '')
        assert JournalAuditModel.objects.filter(action='admin_expire', details__apres='hote').count() == 1

    def test_keeps_rights_before_the_date(self, make_user):
        admin = make_user(role='admin', admin_expire_le=timezone.now() + timedelta(hours=1))
        assert _client_jwt(admin).get(ADMIN + 'avis/').status_code == 200

    def test_defaults_to_traveller_without_a_previous_role(self, make_user):
        admin = make_user(role='admin', admin_expire_le=timezone.now() - timedelta(minutes=1))
        _client_jwt(admin).get(ADMIN + 'avis/')
        admin.refresh_from_db()
        assert admin.role == 'voyageur'

    def test_scheduled_task_covers_admins_who_no_longer_sign_in(self, make_user):
        expire = make_user(role='admin', role_avant_admin='agent', admin_expire_le=timezone.now() - timedelta(days=1))
        encore = make_user(role='admin', admin_expire_le=timezone.now() + timedelta(days=1))
        call_command('retirer_admins_expires', stdout=StringIO())
        expire.refresh_from_db()
        encore.refresh_from_db()
        assert (expire.role, encore.role) == ('agent', 'admin')


class TestSuperAdminCommand:
    def test_promotes_an_existing_account(self, make_user):
        compte = make_user(role='admin', admin_sections=['avis'], admin_expire_le=timezone.now() + timedelta(days=1))
        call_command('super_admin', compte.email, stdout=StringIO())
        compte.refresh_from_db()
        assert compte.is_superuser and compte.is_staff and compte.admin_sections is None and compte.admin_expire_le is None

    def test_removes_a_super_admin_but_never_the_last_one(self, make_user):
        premier = make_user(role='admin', is_superuser=True)
        second = make_user(role='admin', is_superuser=True)
        call_command('super_admin', second.email, '--retirer', stdout=StringIO())
        second.refresh_from_db()
        assert not second.is_superuser and second.role == 'admin'
        with pytest.raises(CommandError, match='dernier'):
            call_command('super_admin', premier.email, '--retirer', stdout=StringIO())

    def test_unknown_account(self):
        with pytest.raises(CommandError, match='Aucun compte'):
            call_command('super_admin', 'personne@example.com', stdout=StringIO())
        assert not UserModel.objects.filter(is_superuser=True).exists()
