"""Waiting list for the opening of the listings."""
from django.core import mail
from rest_framework.test import APIClient

from apps.hebergements.models import InscriptionLancementModel

URL = '/api/v1/hebergements/lancement/'
ADMIN = '/api/v1/admin/lancement/'


def test_inscription_publique_idempotente():
    client = APIClient()
    assert client.post(URL, {'email': 'Ama@Exemple.tg', 'langue': 'en'}, format='json').status_code == 201
    assert client.post(URL, {'email': 'ama@exemple.tg'}, format='json').status_code == 201  # already signed up: same response
    assert client.post(URL, {'email': 'pas-un-email'}, format='json').status_code == 400
    inscription = InscriptionLancementModel.objects.get()
    assert inscription.email == 'ama@exemple.tg' and inscription.langue == 'en'


def test_prevenir_les_inscrits_a_l_ouverture(client_for, make_user, make_hebergement):
    for email, langue in (('ama@exemple.tg', 'fr'), ('john@example.com', 'en')):
        InscriptionLancementModel.objects.create(email=email, langue=langue)
    assert client_for(make_user()).post(ADMIN).status_code == 403
    admin = client_for(make_user(role='admin'))
    make_hebergement(statut_verification='en_attente')  # not published yet
    assert admin.get(ADMIN).data == {'inscrits': 2, 'a_prevenir': 2, 'logements_publies': 0}
    assert admin.post(ADMIN).status_code == 409 and not mail.outbox

    make_hebergement()  # published
    reponse = admin.post(ADMIN)
    assert reponse.status_code == 200 and reponse.data == {'envoyes': 2, 'a_prevenir': 0}
    sujets = {m.to[0]: m.subject for m in mail.outbox}
    assert sujets == {'ama@exemple.tg': 'Kwa-Ba : les logements sont en ligne', 'john@example.com': 'Kwa-Ba: places to stay are now online'}
    assert admin.post(ADMIN).data['envoyes'] == 0  # nobody is notified twice
