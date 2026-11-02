import hashlib

import pytest

from apps.contrats import preinscription
from apps.contrats.models import PreinscriptionModel

PREINSCRIPTION = '/api/v1/contrats/preinscription/'
HEBERGEMENTS = '/api/v1/hebergements/'


def _annonce():
    return {
        'latitude': 6.13, 'longitude': 1.22,
        'name': 'Villa Océane', 'type': 'villa', 'city': 'Lomé', 'location': 'Baguida', 'price_per_night': 85000,
        'max_guests': 6, 'amenities': ['wifi'], 'image_url': 'https://images.unsplash.com/photo-1.jpg',
        'surface_m2': 140, 'chambres': 3, 'salles_de_bain': 2, 'lits_doubles': 2, 'lits_simples': 2, 'canapes_lits': 0,
        'petit_dejeuner': 'inclus', 'arrivee_a_partir': '14:00', 'depart_avant': '11:00',
    }


def _accepter(client, **extra):
    corps = {'accepte': True, 'version': preinscription.VERSION, 'langue': 'fr', **extra}
    return client.post(PREINSCRIPTION, corps, format='json', HTTP_USER_AGENT='Mozilla/5.0 test')


@pytest.fixture
def prelancement(settings):
    settings.PRELANCEMENT = True


def test_text_is_served_in_the_site_language(client_for, make_user, settings):
    client = client_for(make_user(role='hote'))

    fr = client.get(PREINSCRIPTION, HTTP_ACCEPT_LANGUAGE='fr').data
    en = client.get(PREINSCRIPTION, HTTP_ACCEPT_LANGUAGE='en').data

    assert fr['requise'] is False and fr['acceptee'] is False and fr['version'] == preinscription.VERSION
    assert 'Kwaba SAS' in fr['texte'] and fr['texte'].startswith('Kwa-Ba est exploitée')
    assert en['langue'] == 'en' and en['texte'].startswith('Kwa-Ba is operated by Kwaba SAS')
    settings.PRELANCEMENT = True
    assert client.get(PREINSCRIPTION).data['requise'] is True


def test_acceptance_records_the_proof_once(client_for, make_user):
    hote = make_user(role='hote')
    client = client_for(hote)

    assert _accepter(client).status_code == 201
    assert _accepter(client, langue='en').status_code == 201

    proof = PreinscriptionModel.objects.get(hote_id=hote.pk)
    assert proof.version == preinscription.VERSION and proof.langue == 'fr'
    assert proof.empreinte_texte == hashlib.sha256(preinscription.TEXTES['fr'].encode()).hexdigest()
    assert proof.ip == '127.0.0.1' and proof.user_agent == 'Mozilla/5.0 test'
    assert client.get(PREINSCRIPTION).data['acceptee'] is True


def test_acceptance_needs_the_box_ticked_and_the_current_text(client_for, make_user):
    client = client_for(make_user(role='hote'))

    assert _accepter(client, accepte=False).status_code == 400
    assert _accepter(client, accepte='true').status_code == 400
    assert _accepter(client, version=preinscription.VERSION + 1).status_code == 409
    assert _accepter(client, langue='de').status_code == 400
    assert not PreinscriptionModel.objects.exists()


def test_only_hosts_can_pre_register(client_for, make_user):
    assert _accepter(client_for(make_user())).status_code == 403


@pytest.mark.usefixtures('prelancement')
def test_listing_creation_waits_for_the_pre_registration(client_for, make_user):
    client = client_for(make_user(role='hote'))

    refused = client.post(HEBERGEMENTS, _annonce(), format='json')
    assert refused.status_code == 403 and refused.data['code'] == 'preinscription_requise'

    _accepter(client)
    assert client.post(HEBERGEMENTS, _annonce(), format='json').status_code == 201


@pytest.mark.usefixtures('prelancement')
def test_admins_are_not_asked_to_pre_register(client_for, make_user):
    admin = make_user(role='admin', phone='+22990000001')
    assert client_for(admin).post(HEBERGEMENTS, _annonce(), format='json').status_code == 201


def test_no_pre_registration_outside_the_pre_launch(client_for, make_user):
    assert client_for(make_user(role='hote')).post(HEBERGEMENTS, _annonce(), format='json').status_code == 201
