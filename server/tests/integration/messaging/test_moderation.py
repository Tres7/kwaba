import datetime

import pytest
from django.core import mail
from django.utils import timezone

from apps.messaging.infrastructure.persistence import moderation_retention
from apps.messaging.infrastructure.persistence.models import (
    MessageModel, MessageReportModel, NotificationOutboxModel, SanctionModel,
)
from apps.activity.models import ActivityEntryModel, ActivityHoldModel
from apps.securite.models import AlerteFraudeModel

CONVERSATIONS = '/api/v1/messaging/conversations/'
MODERATION = '/api/v1/messaging/moderation/'
ADMIN = '/api/v1/admin/anti-fraude/'
INSULT = "Tu es un imbécile"
THREAT = "Je vais te tuer"


@pytest.fixture
def enforce(settings):
    settings.MODERATION = {**settings.MODERATION, 'MODE': 'enforce'}


@pytest.fixture
def observe(settings):
    settings.MODERATION = {**settings.MODERATION, 'MODE': 'observe'}


@pytest.fixture
def listing(make_hebergement):
    return make_hebergement(name='Villa Océane')


@pytest.fixture
def guest(make_user):
    return make_user(first_name='Ama', last_name='Mensah', email='ama@example.tg')


@pytest.fixture
def host(listing):
    return listing.host


@pytest.fixture
def admin(make_user):
    return make_user(role='admin', email='admin@kwa-ba.com')


@pytest.fixture
def thread(client_for, guest, listing):
    return client_for(guest).post(CONVERSATIONS, {'hebergement_id': str(listing.id)}, format='json').data['id']


def send(client, thread, text, **extra):
    return client.post(f'{CONVERSATIONS}{thread}/messages/', {'content': text, **extra}, format='json')


def report(client, thread, message_id, reason='insult', details=''):
    return client.post(f'{CONVERSATIONS}{thread}/messages/{message_id}/report/',
                       {'reason': reason, 'details': details}, format='json')


def admin_mails(word):
    return [m for m in mail.outbox if word in m.subject]


def host_message(client_for, host, thread, text=INSULT):
    return send(client_for(host), thread, text).data['id']


class TestSending:

    def test_enforce_refuses_and_records_without_delivering(self, enforce, client_for, guest, thread):
        response = send(client_for(guest), thread, INSULT)
        assert response.status_code == 422
        assert response.data['code'] == 'abusive_content' and response.data['categories'] == ['insult']
        assert 'imbécile' not in str(response.data)
        assert not MessageModel.objects.exists() and not NotificationOutboxModel.objects.exists()
        alert = AlerteFraudeModel.objects.get()
        assert (alert.kind, alert.types, alert.extraits, alert.traitee) == ('refusal', ['insult'], [INSULT], False)

    def test_admins_alerted_at_third_real_refusal(self, enforce, client_for, guest, thread, admin,
                                                  django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            for _ in range(4):
                send(client_for(guest), thread, INSULT)
        assert len(admin_mails('messages refusés')) == 1

    def test_warning_needs_explicit_confirmation(self, enforce, client_for, guest, thread):
        client = client_for(guest)
        first = send(client, thread, "Vous êtes un escroc")
        assert first.status_code == 422 and first.data['code'] == 'confirmation_required'
        assert not AlerteFraudeModel.objects.exists()
        assert send(client, thread, "Vous êtes un escroc", confirmed='true').status_code == 422
        assert send(client, thread, "Vous êtes un escroc", confirmed=True).status_code == 201
        assert AlerteFraudeModel.objects.get().kind == 'warning_ignored'

    def test_observe_delivers_and_records_simulated_refusal(self, observe, client_for, guest, thread):
        response = send(client_for(guest), thread, INSULT)
        assert response.status_code == 201
        assert MessageModel.objects.get().content == INSULT
        assert AlerteFraudeModel.objects.get().kind == 'simulated'

    def test_off_mode_records_nothing(self, settings, client_for, guest, thread):
        settings.MODERATION = {**settings.MODERATION, 'MODE': 'off'}
        assert send(client_for(guest), thread, INSULT).status_code == 201
        assert not AlerteFraudeModel.objects.exists()

    def test_default_mode_is_observe(self, settings, client_for, guest, thread):
        settings.MODERATION = {k: v for k, v in settings.MODERATION.items() if k != 'MODE'}
        assert send(client_for(guest), thread, INSULT).status_code == 201
        assert AlerteFraudeModel.objects.get().kind == 'simulated'

    def test_bypass_threshold_ignores_moderation_entries(self, observe, client_for, guest, thread, admin,
                                                         django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            for _ in range(3):
                send(client_for(guest), thread, INSULT)
            send(client_for(guest), thread, "Appelez-moi au 90 12 34 56")
        assert admin_mails('Anti-fraude') == []


class TestDraftCheck:

    def test_enforce_returns_level_and_categories_only(self, enforce, client_for, guest):
        response = client_for(guest).post(f'{MODERATION}check/', {'content': INSULT}, format='json')
        assert response.data == {'level': 'block', 'categories': ['insult']}
        assert not AlerteFraudeModel.objects.exists()

    def test_observe_never_greys_the_send_button(self, observe, client_for, guest):
        response = client_for(guest).post(f'{MODERATION}check/', {'content': INSULT}, format='json')
        assert response.data == {'level': 'allow', 'categories': []}

    def test_false_positive_is_recorded_for_review(self, enforce, client_for, guest, thread):
        client = client_for(guest)
        response = client.post(f'{CONVERSATIONS}{thread}/false-positive/', {'content': "Ce con­cert est nul"}, format='json')
        assert response.status_code == 201 and response.data['recorded'] is False
        client.post(f'{CONVERSATIONS}{thread}/false-positive/', {'content': INSULT}, format='json')
        assert AlerteFraudeModel.objects.get().kind == 'false_positive'


class TestThreatAlerts:

    def test_first_threat_alerts_admins_at_once_then_groups(self, observe, client_for, guest, thread, admin,
                                                           django_capture_on_commit_callbacks):
        for _ in range(2):
            with django_capture_on_commit_callbacks(execute=True):
                send(client_for(guest), thread, THREAT)
        assert len(admin_mails('Menace')) == 1
        assert AlerteFraudeModel.objects.filter(threat_notified_at__isnull=True).count() == 1

        AlerteFraudeModel.objects.update(cree_le=timezone.now() - datetime.timedelta(hours=2))
        from apps.securite import limites
        limites.reinitialiser(f'moderation-threat-email:{guest.id}')
        moderation_retention.purge()
        assert len(admin_mails('Menace')) == 2
        assert not AlerteFraudeModel.objects.filter(threat_notified_at__isnull=True).exists()

    def test_threat_report_alerts_admins(self, observe, client_for, guest, host, thread, admin,
                                         django_capture_on_commit_callbacks):
        message_id = host_message(client_for, host, thread, "Bonjour")
        mail.outbox.clear()
        with django_capture_on_commit_callbacks(execute=True):
            report(client_for(guest), thread, message_id, reason='threat')
        assert len(admin_mails('Menace')) == 1


class TestReports:

    def test_report_snapshots_the_context(self, settings, observe, client_for, guest, host, thread):
        settings.MODERATION = {**settings.MODERATION, 'CONTEXT_MESSAGES': 3}
        for i in range(5):
            send(client_for(guest), thread, f"Question {i}")
        old = MessageModel.objects.order_by('id').first()
        old.created_at = timezone.now() - datetime.timedelta(days=8)
        old.save()
        message_id = host_message(client_for, host, thread)
        response = report(client_for(guest), thread, message_id, details="Il m'insulte")
        assert response.status_code == 201
        saved = MessageReportModel.objects.get()
        assert (saved.author_id, saved.reporter_id, saved.status) == (host.id, guest.id, 'pending')
        assert [c['content'] for c in saved.context] == ["Question 2", "Question 3", "Question 4", INSULT]
        assert saved.context[-1]['reported'] and saved.context[-1]['from_author']
        assert not saved.context[0]['from_author']
        alert = AlerteFraudeModel.objects.get(kind='report')
        assert alert.utilisateur_id == host.id and alert.types == ['insult']

    def test_report_rules(self, observe, client_for, guest, host, thread, make_user):
        own = send(client_for(guest), thread, "Bonjour").data['id']
        assert report(client_for(guest), thread, own).status_code == 403
        message_id = host_message(client_for, host, thread)
        assert report(client_for(guest), thread, message_id, reason='rien').status_code == 400
        assert report(client_for(guest), thread, message_id).status_code == 201
        assert report(client_for(guest), thread, message_id).status_code == 200
        assert report(client_for(make_user()), thread, message_id).status_code == 404
        assert report(client_for(guest), thread, 999999).status_code == 404
        assert MessageReportModel.objects.count() == 1

    def test_author_is_not_notified(self, observe, client_for, guest, host, thread):
        message_id = host_message(client_for, host, thread)
        mail.outbox.clear()
        report(client_for(guest), thread, message_id)
        assert mail.outbox == []


def confirm(client, report_id, note=''):
    return client.post(f'{ADMIN}reports/{report_id}/confirm/', {'note': note}, format='json')


@pytest.fixture
def reported(observe, client_for, guest, host, thread):
    def _reported(count=1):
        ids = []
        for _ in range(count):
            message_id = host_message(client_for, host, thread)
            ids.append(report(client_for(guest), thread, message_id).data['id'])
        return ids
    return _reported


class TestSanctions:

    def test_only_admins_reach_reports(self, client_for, guest, reported):
        report_id, = reported()
        assert client_for(guest).get(f'{ADMIN}reports/{report_id}/').status_code == 403

    def test_viewing_a_report_is_audited(self, client_for, admin, reported, host, guest):
        report_id, = reported()
        detail = client_for(admin).get(f'{ADMIN}reports/{report_id}/').data
        assert detail['author']['email'] == host.email and detail['reporter']['email'] == guest.email
        assert detail['context'][-1]['content'] == INSULT
        assert ActivityEntryModel.objects.filter(action='report_viewed', details__report=report_id).exists()

    def test_ladder_up_to_suspension(self, client_for, admin, host, thread, reported, django_capture_on_commit_callbacks):
        ids = reported(5)
        client = client_for(admin)
        with django_capture_on_commit_callbacks(execute=True):
            steps = [confirm(client, i).data['step'] for i in ids]
        assert steps == ['reminder', 'reminder', 'formal_warning', 'formal_warning', 'short_suspension']
        assert confirm(client, ids[0]).status_code == 409
        to_host = [m for m in mail.outbox if m.to == [host.email]]
        assert [m.subject for m in to_host][-1] == '[Kwa-Ba] Votre messagerie est suspendue'
        assert all('Ama' not in m.body and 'Mensah' not in m.body for m in to_host)

        blocked = send(client_for(host), thread, "Bonjour")
        assert blocked.status_code == 403 and blocked.data['code'] == 'messaging_suspended'
        assert client_for(host).get(f'{CONVERSATIONS}{thread}/messages/').status_code == 200
        status = client_for(host).get(f'{MODERATION}status/').data
        assert status['suspended_until'] is not None and status['sanctions'][0]['step'] == 'short_suspension'
        assert AlerteFraudeModel.objects.filter(kind='report', traitee=False).count() == 0
        assert AlerteFraudeModel.objects.filter(kind='sanction').count() == 5

    def test_rejected_reports_flag_abusive_reporter(self, client_for, admin, guest, reported,
                                                    django_capture_on_commit_callbacks):
        ids = reported(3)
        with django_capture_on_commit_callbacks(execute=True):
            for i in ids:
                assert client_for(admin).post(f'{ADMIN}reports/{i}/reject/', {'note': 'RAS'}, format='json').status_code == 200
        assert not SanctionModel.objects.exists()
        flagged = AlerteFraudeModel.objects.get(kind='abusive_reporter')
        assert flagged.utilisateur_id == guest.id
        assert len(admin_mails('signalements rejetés')) == 1

    def test_contest_by_another_admin_cancels_the_suspension(self, client_for, admin, host, thread, reported,
                                                             make_user):
        ids = reported(5)
        for i in ids:
            confirm(client_for(admin), i)
        suspension = SanctionModel.objects.get(step='short_suspension')
        user = client_for(host)
        assert user.post(f'{MODERATION}sanctions/{suspension.id}/contest/', {'text': 'non'}, format='json').status_code == 400
        assert user.post(f'{MODERATION}sanctions/{suspension.id}/contest/', {'text': "C'était une blague"},
                         format='json').status_code == 200
        assert user.post(f'{MODERATION}sanctions/{suspension.id}/contest/', {'text': 'Encore une fois'},
                         format='json').status_code == 409
        assert AlerteFraudeModel.objects.get(kind='contest').traitee is False

        other = client_for(make_user(role='admin'))
        same = client_for(admin).post(f'{ADMIN}sanctions/{suspension.id}/contest/', {'accept': True}, format='json')
        assert same.status_code == 409
        accepted = other.post(f'{ADMIN}sanctions/{suspension.id}/contest/', {'accept': True, 'note': 'OK'}, format='json')
        assert accepted.status_code == 200 and accepted.data['contest_status'] == 'accepted'
        assert MessageReportModel.objects.get(pk=suspension.report_id).status == 'rejected'
        assert send(user, thread, "Bonjour").status_code == 201

    def test_single_admin_may_review_own_confirmation(self, client_for, admin, host, reported):
        report_id, = reported()
        sanction_id = confirm(client_for(admin), report_id).data['id']
        client_for(host).post(f'{MODERATION}sanctions/{sanction_id}/contest/', {'text': 'Je conteste'}, format='json')
        rejected = client_for(admin).post(f'{ADMIN}sanctions/{sanction_id}/contest/', {'accept': False}, format='json')
        assert rejected.status_code == 200 and rejected.data['contest_status'] == 'rejected'

    def test_contest_window_closes(self, client_for, admin, host, reported):
        report_id, = reported()
        sanction_id = confirm(client_for(admin), report_id).data['id']
        SanctionModel.objects.update(created_at=timezone.now() - datetime.timedelta(days=15))
        response = client_for(host).post(f'{MODERATION}sanctions/{sanction_id}/contest/', {'text': 'Trop tard ?'},
                                         format='json')
        assert response.status_code == 409

    def test_admin_lifts_or_shortens_a_suspension(self, client_for, admin, host, thread, reported):
        for i in reported(5):
            confirm(client_for(admin), i)
        suspension = SanctionModel.objects.get(step='short_suspension')
        shorter = (timezone.now() + datetime.timedelta(hours=1)).isoformat()
        assert client_for(admin).post(f'{ADMIN}sanctions/{suspension.id}/lift/', {'ends_at': shorter},
                                      format='json').status_code == 200
        assert client_for(admin).post(f'{ADMIN}sanctions/{suspension.id}/lift/', {}, format='json').status_code == 200
        assert send(client_for(host), thread, "Bonjour").status_code == 201
        assert ActivityEntryModel.objects.filter(action='sanction_lifted').count() == 2


class TestRetention:

    def test_purge_follows_the_retention_table(self, client_for, admin, reported, guest, thread, settings):
        rejected, confirmed, held = reported(3)
        settings.MODERATION = {**settings.MODERATION, 'MODE': 'enforce'}
        send(client_for(guest), thread, INSULT)
        client_for(admin).post(f'{ADMIN}reports/{rejected}/reject/', format='json')
        confirm(client_for(admin), confirmed)
        confirm(client_for(admin), held)
        client_for(admin).post(f'{ADMIN}reports/{held}/legal-hold/', {'hold': True}, format='json')
        assert ActivityHoldModel.objects.filter(target_kind='report', target_id=str(held)).exists()

        now = timezone.now()
        moderation_retention.purge(now + datetime.timedelta(days=91))
        assert MessageReportModel.objects.get(pk=rejected).context == []
        assert MessageReportModel.objects.get(pk=confirmed).context != []
        assert AlerteFraudeModel.objects.get(kind='refusal').extraits == []
        assert AlerteFraudeModel.objects.get(kind='report', objet_id=str(held)).extraits != []

        AlerteFraudeModel.objects.update(cree_le=now - datetime.timedelta(days=91))
        moderation_retention.purge(now + datetime.timedelta(days=366))
        assert not MessageReportModel.objects.filter(pk=rejected).exists()
        assert MessageReportModel.objects.get(pk=confirmed).context == []
        assert MessageReportModel.objects.get(pk=held).context != []
        assert AlerteFraudeModel.objects.get(kind='report', objet_id=str(held)).extraits != []

        moderation_retention.purge(now + datetime.timedelta(days=731))
        assert list(MessageReportModel.objects.values_list('pk', flat=True)) == [held]
        assert list(SanctionModel.objects.values_list('report_id', flat=True)) == [held]
