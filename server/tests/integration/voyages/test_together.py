"""Kwa-Ba Together: group trip, invitation, votes, budget per person, itinerary."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

VOYAGES = '/api/v1/voyages/'


@pytest.fixture
def client_for():
    """One client per user: several members act in the same test."""
    def _client(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client
    return _client


def _dates(dans=30, nuits=4):
    debut = timezone.localdate() + timedelta(days=dans)
    return debut.isoformat(), (debut + timedelta(days=nuits)).isoformat()


def _creer(client, **champs):
    debut, fin = _dates()
    r = client.post(VOYAGES, {'nom': 'Abidjan entre amis', 'destination': 'Abidjan', 'date_debut': debut,
                              'date_fin': fin, 'nb_voyageurs': 4, **champs}, format='json')
    assert r.status_code == 201, r.data
    return r.data


def _rejoindre(client_for, user, voyage):
    client = client_for(user)
    assert client.post(f"{VOYAGES}invitations/{voyage['code_invitation']}/").status_code == 200
    return client


def test_creer_inviter_rejoindre(client_for, make_user):
    orga = client_for(make_user(first_name='Ama', last_name='Kossi'))
    v = _creer(orga)
    assert v['est_organisateur'] and len(v['membres']) == 1

    invite = client_for(make_user(first_name='Kofi'))
    apercu = invite.get(f"{VOYAGES}invitations/{v['code_invitation']}/").data
    assert (apercu['nom'], apercu['organisateur'], apercu['deja_membre']) == ('Abidjan entre amis', 'Ama K.', False)
    # Before joining, the trip is invisible
    assert invite.get(f"{VOYAGES}{v['id']}/").status_code == 404
    assert invite.post(f"{VOYAGES}invitations/{v['code_invitation']}/").status_code == 200
    assert invite.post(f"{VOYAGES}invitations/{v['code_invitation']}/").status_code == 200  # idempotent
    assert len(invite.get(f"{VOYAGES}{v['id']}/").data['membres']) == 2
    assert len(invite.get(VOYAGES).data['results']) == 1


def test_votes_et_budget_par_personne(client_for, make_user, make_hebergement):
    orga = client_for(make_user())
    v = _creer(orga)
    ami = _rejoindre(client_for, make_user(), v)
    appart = make_hebergement(name='Appartement Cocody', city='Abidjan', price_per_night=40000, max_guests=4)
    villa = make_hebergement(name='Villa Assinie', city='Abidjan', price_per_night=90000, max_guests=8)

    d = orga.post(f"{VOYAGES}{v['id']}/propositions/", {'hebergement': str(appart.id), 'commentaire': 'Central'},
                  format='json').data
    ami.post(f"{VOYAGES}{v['id']}/propositions/", {'hebergement': str(villa.id)}, format='json')
    doublon = orga.post(f"{VOYAGES}{v['id']}/propositions/", {'hebergement': str(appart.id)}, format='json')
    assert doublon.status_code == 409

    p_appart = next(p for p in d['propositions'] if p['hebergement']['name'] == 'Appartement Cocody')
    # 4 nights x 40,000 + 6 % = 169,600, for 4: 42,400 each
    assert p_appart['budget'] == {'nuits': 4, 'total': 169600, 'par_personne': 42400, 'personnes': 4}
    assert p_appart['disponible'] is True and p_appart['assez_grand'] is True

    d = ami.get(f"{VOYAGES}{v['id']}/").data
    p_villa = next(p for p in d['propositions'] if p['hebergement']['name'] == 'Villa Assinie')
    orga.post(f"{VOYAGES}{v['id']}/vote/", {'proposition': p_villa['id']}, format='json')
    d = ami.post(f"{VOYAGES}{v['id']}/vote/", {'proposition': p_villa['id']}, format='json').data
    assert d['propositions'][0]['hebergement']['name'] == 'Villa Assinie'  # sorted by votes
    assert d['propositions'][0]['votes'] == 2 and d['mon_vote'] == p_villa['id']

    # Changing one's mind: a single vote per member
    d = ami.post(f"{VOYAGES}{v['id']}/vote/", {'proposition': p_appart['id']}, format='json').data
    assert sorted(p['votes'] for p in d['propositions']) == [1, 1]


def test_seul_l_organisateur_retient_et_modifie(client_for, make_user, make_hebergement):
    orga = client_for(make_user())
    v = _creer(orga)
    ami = _rejoindre(client_for, make_user(), v)
    h = make_hebergement(city='Abidjan')
    d = ami.post(f"{VOYAGES}{v['id']}/propositions/", {'hebergement': str(h.id)}, format='json').data
    pid = d['propositions'][0]['id']

    assert ami.post(f"{VOYAGES}{v['id']}/retenir/", {'proposition': pid}, format='json').status_code == 403
    retenu = orga.post(f"{VOYAGES}{v['id']}/retenir/", {'proposition': pid}, format='json')
    assert retenu.data['proposition_retenue'] == pid
    assert ami.patch(f"{VOYAGES}{v['id']}/", {'nom': 'Autre nom'}, format='json').status_code == 403
    assert ami.patch(f"{VOYAGES}{v['id']}/", {'notes': 'Vol AF 520 arrive à 14 h'}, format='json').status_code == 200
    assert ami.delete(f"{VOYAGES}{v['id']}/").status_code == 403


def test_itineraire_et_reservations_partagees(client_for, make_user, make_hebergement):
    orga = client_for(make_user())
    v = _creer(orga)
    ami = _rejoindre(client_for, make_user(first_name='Kofi'), v)

    jour = _dates()[0]
    ami.post(f"{VOYAGES}{v['id']}/etapes/", {'date': jour, 'heure': '10:00', 'titre': 'Marché de Treichville',
                                             'lieu': 'Treichville'}, format='json')
    orga.post(f"{VOYAGES}{v['id']}/etapes/", {'date': jour, 'heure': '08:30', 'titre': 'Petit-déjeuner'}, format='json')
    etapes = orga.get(f"{VOYAGES}{v['id']}/").data['etapes']
    assert [e['titre'] for e in etapes] == ['Petit-déjeuner', 'Marché de Treichville']  # sorted by time

    # Sharing a booking: only one's own
    h = make_hebergement(city='Abidjan', price_per_night=30000)
    debut = timezone.localdate() + timedelta(days=30)
    r = ami.post('/api/v1/reservations/', {'hebergement': str(h.id), 'check_in': debut.isoformat(),
                                           'check_out': (debut + timedelta(days=2)).isoformat(), 'guests_count': 2},
                 format='json')
    rid = r.data['id']
    assert orga.post(f"{VOYAGES}{v['id']}/reservations/", {'reservation': rid}, format='json').status_code == 400
    d = ami.post(f"{VOYAGES}{v['id']}/reservations/", {'reservation': rid}, format='json').data
    assert d['reservations'][0]['reference'].startswith('RES-')
    assert orga.get(f"{VOYAGES}{v['id']}/").data['reservations'][0]['reserve_par'].startswith('Kofi')


def test_quitter_retirer_et_nouveau_lien(client_for, make_user):
    orga_user, ami_user = make_user(), make_user()
    orga = client_for(orga_user)
    v = _creer(orga)
    ami = _rejoindre(client_for, ami_user, v)

    assert ami.delete(f"{VOYAGES}{v['id']}/membres/{orga_user.id}/").status_code == 403
    assert orga.delete(f"{VOYAGES}{v['id']}/membres/{orga_user.id}/").status_code == 400
    assert ami.delete(f"{VOYAGES}{v['id']}/membres/{ami_user.id}/").status_code == 204
    assert ami.get(f"{VOYAGES}{v['id']}/").status_code == 404

    ancien = v['code_invitation']
    nouveau = orga.post(f"{VOYAGES}{v['id']}/nouveau-lien/").data['code_invitation']
    assert nouveau != ancien
    assert ami.post(f"{VOYAGES}invitations/{ancien}/").status_code == 404


def test_dates_coherentes(client_for, make_user):
    orga = client_for(make_user())
    debut, fin = _dates()
    r = orga.post(VOYAGES, {'nom': 'X', 'destination': 'Lomé', 'date_debut': fin, 'date_fin': debut}, format='json')
    assert r.status_code == 400 and 'date_fin' in r.data
    sans_dates = orga.post(VOYAGES, {'nom': 'Plus tard', 'destination': 'Lomé'}, format='json')
    assert sans_dates.status_code == 201 and sans_dates.data['nuits'] is None
