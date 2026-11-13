from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.activity import api as activity
from apps.activity.models import ActivityEntryModel, ActivityHoldModel

URL = '/api/v1/admin/activity/'


@pytest.fixture
def super_admin(make_user):
    return make_user(role='admin', is_superuser=True, is_staff=True, first_name='Ama', last_name='Admin')


@pytest.fixture
def client(super_admin, client_for):
    return client_for(super_admin)


def _entry(action, *, days_ago=0, **fields):
    entry = ActivityEntryModel.objects.create(action=action, **fields)
    if days_ago:
        ActivityEntryModel.objects.filter(pk=entry.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
    return entry


class TestRecord:
    def test_role_change_by_an_admin_keeps_the_author_and_the_target_apart(self, client, super_admin, make_user):
        traveller = make_user(first_name='Jean', last_name='Kouamé')
        response = client.patch(f'/api/v1/admin/users/{traveller.pk}/', {'role': 'agent'}, format='json')
        assert response.status_code == 200
        entry = ActivityEntryModel.objects.get(action='role_modifie')
        assert entry.actor_id == super_admin.pk and entry.actor_email == super_admin.email
        assert entry.actor_role == 'admin'
        assert (entry.target_kind, entry.target_id, entry.target_label) == ('account', str(traveller.pk),
                                                                           traveller.email)

    def test_recording_never_breaks_the_request(self, monkeypatch):
        monkeypatch.setattr(ActivityEntryModel.objects, 'create', lambda **kw: (_ for _ in ()).throw(RuntimeError))
        activity.record('connexion', email='x@example.tg')


class TestList:
    def test_routine_events_are_hidden_by_default(self, client):
        _entry('connexion', actor_email='a@x.tg')
        _entry('role_modifie', actor_email='b@x.tg')
        _entry('annonce_verifiee', actor_email='c@x.tg')
        default = [e['action'] for e in client.get(URL).data['results']]
        assert set(default) == {'role_modifie', 'annonce_verifiee'}
        sensitive = [e['action'] for e in client.get(URL, {'level': 'sensitive'}).data['results']]
        assert sensitive == ['role_modifie']
        everything = [e['action'] for e in client.get(URL, {'level': 'all'}).data['results']]
        assert set(everything) == {'connexion', 'role_modifie', 'annonce_verifiee'}

    def test_readable_entry(self, client, super_admin, make_user):
        traveller = make_user(first_name='Jean', last_name='Kouamé')
        activity.record('role_modifie', actor=super_admin, ip=None,
                        target=activity.Target('account', str(traveller.pk), traveller.email),
                        avant='voyageur', apres='hote')
        entry = client.get(URL).data['results'][0]
        assert entry['label'] == 'Rôle modifié' and entry['category'] == 'rights' and entry['level'] == 'sensitive'
        assert entry['summary'] == 'Jean Kouamé · voyageur → hote'
        assert entry['actor']['name'] == 'Ama Admin'
        assert entry['target'] == {'kind': 'account', 'kind_label': 'Compte', 'id': str(traveller.pk),
                                   'label': 'Jean Kouamé'}

    def test_counts_by_category_and_today_banner(self, client):
        _entry('connexion_bloquee', actor_email='a@x.tg')
        _entry('code_bloque', actor_email='a@x.tg')
        _entry('visit_moved')
        data = client.get(URL, {'category': 'agenda'}).data
        assert [e['action'] for e in data['results']] == ['visit_moved']
        assert data['counts']['connections'] == 2 and data['counts']['agenda'] == 1
        assert data['today'] == {'sensitive': 2, 'blocked': 2}

    def test_search_by_name_email_or_ip_and_filters(self, client, make_user):
        jean = make_user(first_name='Jean', last_name='Kouamé')
        _entry('mdp_reinitialise', actor_id=jean.pk, actor_email=jean.email, ip='41.207.0.1')
        _entry('mdp_reinitialise', actor_email='other@x.tg', ip='10.0.0.1')
        assert len(client.get(URL, {'q': 'Kouamé'}).data['results']) == 1
        assert len(client.get(URL, {'q': 'other@x'}).data['results']) == 1
        assert len(client.get(URL, {'q': '41.207.0.1'}).data['results']) == 1
        assert len(client.get(URL, {'actor': str(jean.pk)}).data['results']) == 1
        assert len(client.get(URL, {'ip': '10.0.0.1'}).data['results']) == 1

    def test_target_filter_shows_everything_about_one_listing(self, client):
        _entry('annonce_verifiee', target_kind='listing', target_id='l1', target_label='Villa')
        _entry('photos_controlees', target_kind='listing', target_id='l1', target_label='Villa')
        _entry('annonce_verifiee', target_kind='listing', target_id='l2', target_label='Studio')
        results = client.get(URL, {'target_kind': 'listing', 'target_id': 'l1'}).data['results']
        assert len(results) == 2

    def test_period_and_pagination(self, client):
        _entry('role_modifie', days_ago=20)
        for _ in range(3):
            _entry('role_modifie')
        assert len(client.get(URL).data['results']) == 3
        assert len(client.get(URL, {'period': '30d'}).data['results']) == 4
        first = client.get(URL, {'period': '30d', 'level': 'all'}).data
        assert first['next'] is None
        older = client.get(URL, {'period': '30d', 'before': first['results'][1]['id']}).data['results']
        assert len(older) == 2

    def test_detail_lines(self, client):
        entry = _entry('validated_without_visit', details={'motif': 'Hôtel connu', 'keep_visit': False})
        data = client.get(f'{URL}{entry.pk}/').data
        assert data['details'] == [{'label': 'Motif', 'value': 'Hôtel connu'},
                                   {'label': 'Visite conservée', 'value': 'non'}]
        assert client.get(f'{URL}999999/').status_code == 404

    def test_unknown_or_legacy_entries_still_show(self, client):
        _entry('old_action', legacy=True, details={'x': 1})
        entry = client.get(URL).data['results'][0]
        assert entry['label'] == 'old_action' and entry['legacy'] is True


class TestExport:
    def test_csv_of_the_current_search_is_itself_logged(self, client, super_admin):
        _entry('role_modifie', actor_email='b@x.tg', details={'avant': 'voyageur', 'apres': 'agent'})
        response = client.get(f'{URL}export/', {'level': 'sensitive'})
        assert response.status_code == 200 and response['Content-Type'] == 'text/csv; charset=utf-8'
        content = response.content.decode('utf-8-sig')
        assert content.splitlines()[0].startswith('date;action;categorie')
        assert 'Rôle modifié' in content and 'b@x.tg' in content
        exported = ActivityEntryModel.objects.get(action='activity_exported')
        assert exported.actor_id == super_admin.pk and exported.details['rows'] == 1


class TestAccess:
    def test_super_admins_and_granted_admins_only(self, make_user, client_for):
        assert client_for(make_user(role='admin')).get(URL).status_code == 403
        granted = make_user(role='admin', admin_permissions=['activity_log'], admin_sections=['avis'])
        assert client_for(granted).get(URL).status_code == 200
        assert client_for(make_user(role='agent')).get(URL).status_code == 403
        assert client_for(make_user(role='admin')).get(f'{URL}export/').status_code == 403


class TestRetention:
    def test_purge_keeps_twelve_months_and_legal_holds(self):
        _entry('connexion', days_ago=400)
        _entry('report_viewed', days_ago=400, target_kind='report', target_id='7')
        _entry('report_viewed', days_ago=400, target_kind='report', target_id='8')
        recent = _entry('connexion', days_ago=10)
        activity.hold('report', 7, True)
        call_command('purge_activity')
        remaining = set(ActivityEntryModel.objects.values_list('target_id', flat=True))
        assert remaining == {'7', ''} and ActivityEntryModel.objects.filter(pk=recent.pk).exists()
        activity.hold('report', 7, False)
        assert not ActivityHoldModel.objects.exists()
