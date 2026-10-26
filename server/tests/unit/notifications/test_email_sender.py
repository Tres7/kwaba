from pathlib import Path

import pytest

from apps.notifications.application.service.NotificationService import NotificationService
from apps.notifications.infrastructure.email.DjangoEmailSender import DjangoEmailSender

APPS_DIR = Path(__file__).resolve().parents[3] / 'apps'


@pytest.fixture
def notifications():
    return NotificationService(DjangoEmailSender())


def test_verification_email(notifications, mailoutbox):
    notifications.send_verification_email('ama@example.tg', 'Ama', '482913')
    [email] = mailoutbox
    assert email.to == ['ama@example.tg']
    assert 'Vérification' in email.subject
    assert 'Ama' in email.body
    assert '482913' in email.body


def test_welcome_email(notifications, mailoutbox):
    notifications.send_welcome_email('ama@example.tg', 'Ama')
    [email] = mailoutbox
    assert email.subject == 'Bienvenue sur Kwa-Ba'
    assert 'Ama' in email.body


def test_password_reset_email(notifications, mailoutbox):
    notifications.send_password_reset_email('ama@example.tg', 'Ama', '105377')
    [email] = mailoutbox
    assert 'Réinitialisation' in email.subject
    assert '105377' in email.body


def test_new_message_email(notifications, mailoutbox):
    notifications.send_new_message_email('kofi@example.tg', 'Kofi', 'Ama', 'Villa Océane', 'Bonjour, est-ce libre ?',
                                         'https://kwaba.example/messages/42')
    [email] = mailoutbox
    assert email.subject == 'Nouveau message de Ama sur Kwa-Ba'
    for expected in ('Kofi', 'Villa Océane', 'Bonjour, est-ce libre ?', 'https://kwaba.example/messages/42'):
        assert expected in email.body


def test_plain_text_email_keeps_apostrophes(notifications, mailoutbox):
    notifications.send_welcome_email('nguessan@example.tg', "N'Guessan")
    assert "N'Guessan" in mailoutbox[0].body


def test_every_text_email_template_disables_html_escaping():
    # A plain text email is not HTML: without autoescape off, "N'Guessan" becomes "N&#x27;Guessan"
    templates = sorted(APPS_DIR.glob('*/templates/emails/**/*.txt'))
    assert templates
    unprotected = [
        str(t.relative_to(APPS_DIR)) for t in templates
        if not t.read_text().lstrip().startswith('{% autoescape off %}')
        or not t.read_text().rstrip().endswith('{% endautoescape %}')
    ]
    assert unprotected == []
