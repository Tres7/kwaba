from apps.notifications import api


def test_an_event_without_an_email_is_ignored(mailoutbox):
    api.traiter('users.user_registered', {'email': 'ama@example.tg'})

    assert mailoutbox == []


def test_a_handled_event_sends_its_email(mailoutbox):
    api.traiter('users.welcome_email_requested', {'email': 'ama@example.tg', 'first_name': 'Ama'})

    assert [m.to for m in mailoutbox] == [['ama@example.tg']]
