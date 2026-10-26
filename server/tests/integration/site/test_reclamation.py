"""Complaint form of the help centre: an email to the contact address, nothing is saved."""
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

URL = '/api/v1/site/reclamation/'
DESCRIPTION = "Le logement n'avait pas d'eau chaude pendant tout le séjour."


def test_reclamation_d_un_client_connecte_avec_piece_jointe(make_user, settings):
    settings.ASSISTANCE_CONTACT = 'info@kwa-ba.com'
    client = APIClient()
    client.force_authenticate(make_user(email='ama@test.kwaba', first_name='Ama', last_name='Mensah'))
    photo = SimpleUploadedFile('douche.jpg', b'\xff\xd8\xff' + b'0' * 100, content_type='image/jpeg')
    r = client.post(URL, {'objet': 'logement', 'reservation': 'RES-AF2026-AB12', 'description': DESCRIPTION,
                          'piece_jointe': photo}, format='multipart')
    assert r.status_code == 201, r.data
    (email,) = mail.outbox
    assert email.to == ['info@kwa-ba.com'] and email.reply_to == ['ama@test.kwaba']
    assert email.subject == 'Réclamation : Logement (RES-AF2026-AB12)'
    assert 'Ama Mensah <ama@test.kwaba> (compte Kwa-Ba)' in email.body and DESCRIPTION in email.body
    assert email.attachments[0][0] == 'douche.jpg'


def test_visiteur_doit_donner_son_email():
    client = APIClient()
    r = client.post(URL, {'objet': 'autre', 'description': DESCRIPTION}, format='multipart')
    assert r.status_code == 400 and 'email' in r.data and not mail.outbox
    r = client.post(URL, {'objet': 'autre', 'email': 'kofi@test.kwaba', 'description': DESCRIPTION}, format='multipart')
    assert r.status_code == 201 and mail.outbox[0].reply_to == ['kofi@test.kwaba']
    assert 'Réservation : non indiquée' in mail.outbox[0].body


def test_pieces_jointes_refusees(make_user):
    client = APIClient()
    client.force_authenticate(make_user())
    script = SimpleUploadedFile('virus.exe', b'MZ', content_type='application/octet-stream')
    r = client.post(URL, {'objet': 'paiement', 'description': DESCRIPTION, 'piece_jointe': script}, format='multipart')
    assert r.status_code == 400 and 'piece_jointe' in r.data
    lourd = SimpleUploadedFile('scan.pdf', b'0' * (5 * 1024 * 1024 + 1), content_type='application/pdf')
    r = client.post(URL, {'objet': 'paiement', 'description': DESCRIPTION, 'piece_jointe': lourd}, format='multipart')
    assert r.status_code == 400 and not mail.outbox
    r = client.post(URL, {'objet': 'paiement', 'description': 'Trop court'}, format='multipart')
    assert r.status_code == 400 and 'description' in r.data
