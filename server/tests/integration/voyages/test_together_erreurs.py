"""Kwa-Ba Together: refusals and edge cases of the API."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

VOYAGES = '/api/v1/voyages/'
INCONNU = '00000000-0000-0000-0000-000000000000'


@pytest.fixture
def client_for():
    def _client(user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c
    return _client


@pytest.fixture
def voyage(client_for, make_user):
    orga = client_for(make_user())
    debut = timezone.localdate() + timedelta(days=30)
    v = orga.post(VOYAGES, {'nom': 'Lomé', 'destination': 'Lomé', 'date_debut': debut.isoformat(),
                            'date_fin': (debut + timedelta(days=3)).isoformat(), 'nb_voyageurs': 2}, format='json').data
    return orga, v


def test_voyage_inconnu_ou_d_un_autre(client_for, make_user):
    client = client_for(make_user())
    for methode, chemin in (('get', ''), ('patch', ''), ('delete', ''), ('post', 'nouveau-lien/'), ('post', 'propositions/'),
                            ('delete', 'propositions/1/'), ('post', 'vote/'), ('delete', 'vote/'), ('post', 'retenir/'),
                            ('post', 'etapes/'), ('delete', 'etapes/1/'), ('post', 'reservations/'), ('delete', 'reservations/1/'),
                            ('delete', f'membres/{INCONNU}/')):
        assert getattr(client, methode)(f'{VOYAGES}{INCONNU}/{chemin}', {}, format='json').status_code == 404, chemin
    assert client.get(f'{VOYAGES}invitations/inconnu/').status_code == 404
    assert client.post(f'{VOYAGES}invitations/inconnu/').status_code == 404


def test_elements_inconnus_et_droits(client_for, make_user, make_hebergement, voyage):
    orga, v = voyage
    vid = v['id']
    assert orga.post(f'{VOYAGES}{vid}/propositions/', {'hebergement': INCONNU}, format='json').status_code == 400
    assert orga.delete(f'{VOYAGES}{vid}/propositions/999/').status_code == 404
    assert orga.post(f'{VOYAGES}{vid}/vote/', {'proposition': 999}, format='json').status_code == 400
    assert orga.post(f'{VOYAGES}{vid}/retenir/', {'proposition': 999}, format='json').status_code == 400
    assert orga.delete(f'{VOYAGES}{vid}/etapes/999/').status_code == 404
    assert orga.delete(f'{VOYAGES}{vid}/reservations/999/').status_code == 404
    assert orga.post(f'{VOYAGES}{vid}/reservations/', {'reservation': INCONNU}, format='json').status_code == 400

    # A member can neither remove another one's suggestion or step, nor regenerate the link
    ami = client_for(make_user())
    ami.post(f"{VOYAGES}invitations/{v['code_invitation']}/")
    d = orga.post(f'{VOYAGES}{vid}/propositions/', {'hebergement': str(make_hebergement().id)}, format='json').data
    pid = d['propositions'][0]['id']
    assert ami.delete(f'{VOYAGES}{vid}/propositions/{pid}/').status_code == 403
    assert ami.post(f'{VOYAGES}{vid}/retenir/', {'proposition': pid}, format='json').status_code == 403
    assert ami.post(f'{VOYAGES}{vid}/nouveau-lien/').status_code == 403
    jour = (timezone.localdate() + timedelta(days=30)).isoformat()
    e = orga.post(f'{VOYAGES}{vid}/etapes/', {'date': jour, 'titre': 'Plage'}, format='json').data
    assert ami.delete(f"{VOYAGES}{vid}/etapes/{e['etapes'][0]['id']}/").status_code == 403
    assert orga.delete(f"{VOYAGES}{vid}/etapes/{e['etapes'][0]['id']}/").status_code == 204
    assert ami.delete(f'{VOYAGES}{vid}/membres/{make_user().id}/').status_code == 403

    # Remove one's vote, cancel the chosen option, remove the suggestion
    orga.post(f'{VOYAGES}{vid}/vote/', {'proposition': pid}, format='json')
    assert orga.delete(f'{VOYAGES}{vid}/vote/').data['mon_vote'] is None
    orga.post(f'{VOYAGES}{vid}/retenir/', {'proposition': pid}, format='json')
    assert orga.post(f'{VOYAGES}{vid}/retenir/', {'proposition': None}, format='json').data['proposition_retenue'] is None
    assert orga.delete(f'{VOYAGES}{vid}/propositions/{pid}/').status_code == 204
    # Change of the dates by the organiser, then deletion of the trip
    assert orga.patch(f'{VOYAGES}{vid}/', {'nb_voyageurs': 3}, format='json').data['nb_voyageurs'] == 3
    apres_fin = (timezone.localdate() + timedelta(days=40)).isoformat()
    assert orga.patch(f'{VOYAGES}{vid}/', {'date_debut': apres_fin}, format='json').status_code == 400  # arrival after departure
    assert orga.delete(f'{VOYAGES}{vid}/').status_code == 204


def test_reservation_partagee_retiree(client_for, make_user, make_hebergement, voyage, settings):
    settings.FEDAPAY = {**settings.FEDAPAY, 'SECRET_KEY': ''}
    settings.PAYPAL = {'CLIENT_ID': '', 'CLIENT_SECRET': '', 'ENV': 'sandbox'}
    orga, v = voyage
    debut = timezone.localdate() + timedelta(days=30)
    r = orga.post('/api/v1/reservations/', {'hebergement': str(make_hebergement().id), 'check_in': debut.isoformat(),
                                            'check_out': (debut + timedelta(days=2)).isoformat()}, format='json')
    d = orga.post(f"{VOYAGES}{v['id']}/reservations/", {'reservation': r.data['id']}, format='json').data
    lien = d['reservations'][0]['id']
    ami = client_for(make_user())
    ami.post(f"{VOYAGES}invitations/{v['code_invitation']}/")
    assert ami.delete(f"{VOYAGES}{v['id']}/reservations/{lien}/").status_code == 403
    assert orga.delete(f"{VOYAGES}{v['id']}/reservations/{lien}/").status_code == 204
