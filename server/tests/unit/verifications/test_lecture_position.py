"""Position read from what a field agent pastes: coordinates, Google Maps links, WhatsApp locations. No network: the
short-link redirection is simulated, and any other request fails the test."""
from decimal import Decimal

import pytest
import requests

from apps.verifications import positions
from apps.verifications.positions import PositionIllisible, lire

LOME = (Decimal('6.131900'), Decimal('1.222800'))


class Reponse:
    def __init__(self, status_code, location=None):
        self.status_code, self.headers = status_code, ({'Location': location} if location else {})

    def close(self):
        pass


@pytest.fixture
def reseau(monkeypatch):
    """Simulated answers by address; records every request made."""
    demandes, reponses = [], {}

    def get(url, **options):
        assert options['allow_redirects'] is False and options['timeout']
        demandes.append(url)
        if url not in reponses:
            raise AssertionError(f'Requête inattendue : {url}')
        reponse = reponses[url]
        if isinstance(reponse, Exception):
            raise reponse
        return reponse

    monkeypatch.setattr(positions.requests, 'get', get)
    return demandes, reponses


@pytest.mark.parametrize('texte', [
    '6.1319, 1.2228',
    '6.1319,1.2228',
    '6.131900 1.222800',
    '6,1319 ; 1,2228',
    '6,1319, 1,2228',
    'Lat 6.1319 Long 1.2228 (± 8 m)',
    '6°07\'54.8"N 1°13\'22.1"E',
])
def test_coordonnees_ecrites(texte, reseau):
    latitude, longitude = lire(texte)
    assert abs(latitude - LOME[0]) < Decimal('0.0001') and abs(longitude - LOME[1]) < Decimal('0.0001')
    assert reseau[0] == []


@pytest.mark.parametrize('lien', [
    # WhatsApp location opened in Google Maps, then shared
    'Ma position : https://maps.google.com/maps?q=6.1319%2C1.2228&z=17&hl=fr',
    'https://www.google.com/maps?q=6.1319,1.2228',
    'https://www.google.com/maps/search/6.1319,+1.2228?entry=tts',
    'https://www.google.com/maps/@6.1319,1.2228,18z',
    # A place: its marker (!3d!4d) wins over the centre of the view (@)
    'https://www.google.com/maps/place/Villa/@6.1400,1.2300,15z/data=!3m1!4b1!4m6!3m5!8m2!3d6.1319!4d1.2228',
    'https://www.google.tg/maps/place/6%C2%B007\'54.8%22N/@6.1319,1.2228,17z',
])
def test_liens_google_maps_lus_sans_les_ouvrir(lien, reseau):
    assert lire(lien) == LOME
    assert reseau[0] == []


def test_lien_court_suivi_chez_google_seulement(reseau):
    demandes, reponses = reseau
    reponses['https://maps.app.goo.gl/AbCd123'] = Reponse(
        302, 'https://www.google.com/maps/place/Villa/data=!4m2!3m1!1s0x0:0x0!8m2!3d6.1319!4d1.2228?g_st=iw')
    assert lire('https://maps.app.goo.gl/AbCd123') == LOME
    assert demandes == ['https://maps.app.goo.gl/AbCd123']  # the Google Maps page itself is never requested


def test_page_de_consentement_lue_sans_etre_ouverte(reseau):
    reseau[1]['https://maps.app.goo.gl/AbCd123'] = Reponse(
        302, 'https://consent.google.com/ml?continue=https://www.google.com/maps?q%3D6.1319,1.2228&gl=DE')
    assert lire('https://maps.app.goo.gl/AbCd123') == LOME


@pytest.mark.parametrize('suite', [
    'https://evil.example/maps?q=6.1,1.2',     # redirected elsewhere than Google
    'http://maps.app.goo.gl/autre',             # back to plain http
])
def test_lien_court_detourne_refuse(suite, reseau):
    reseau[1]['https://maps.app.goo.gl/AbCd123'] = Reponse(302, suite)
    with pytest.raises(PositionIllisible):
        lire('https://maps.app.goo.gl/AbCd123')
    assert reseau[0] == ['https://maps.app.goo.gl/AbCd123']


@pytest.mark.parametrize('lien', [
    'https://maps.app.goo.gl:8443/AbCd123',
    'https://user@maps.app.goo.gl/AbCd123',
    'https://169.254.169.254/latest/meta-data',
    'https://maps.app.goo.gl.evil.example/AbCd123',
])
def test_aucune_autre_adresse_n_est_demandee(lien, reseau):
    with pytest.raises(PositionIllisible):
        lire(lien)
    assert reseau[0] == []


def test_google_injoignable(reseau):
    reseau[1]['https://maps.app.goo.gl/AbCd123'] = requests.ConnectionError('injoignable')
    with pytest.raises(PositionIllisible, match='ne répond pas'):
        lire('https://maps.app.goo.gl/AbCd123')


def test_lien_court_sans_redirection(reseau):
    reseau[1]['https://maps.app.goo.gl/expire'] = Reponse(404)
    with pytest.raises(PositionIllisible, match='aucune carte'):
        lire('https://maps.app.goo.gl/expire')


@pytest.mark.parametrize('texte, message', [
    ('', 'Collez'),
    ('Derrière la pharmacie', 'illisible'),
    ('6.13, 1.22', 'trop imprécises'),
    ('4Q6J+XX Lomé', 'plus codes'),
    ('https://www.google.com/maps/place/Pharmacie+du+Boulevard', 'ne contient pas'),
    ('95.1319, 1.2228', "n'existent pas"),
    ('0.000000, 0.000000', "n'existent pas"),
])
def test_ce_qui_n_est_pas_une_position(texte, message, reseau):
    with pytest.raises(PositionIllisible, match=message):
        lire(texte)
