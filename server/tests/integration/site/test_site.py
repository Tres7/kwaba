"""Public site settings (config/site.py): module switches and legal numbers, launch state."""
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.concierge import services as concierge
from apps.documents.models import ParametresSocieteModel
from apps.paiements import services as paiements

SITE = '/api/v1/site/'


@pytest.fixture
def lancement(settings):
    """All modules hidden, as at launch (default value outside tests)."""
    settings.MODULES = {nom: False for nom in settings.MODULES}
    return settings


def test_reglages_du_lancement(lancement):
    reglages = APIClient().get(SITE).json()
    assert reglages['modules'] == {
        'experiences': False, 'together': False, 'give': False, 'concierge': False,
        'location_sans_chauffeur': False, 'paiements_non_ouverts': False,
    }
    # Numbers not assigned yet: empty, the site shows "to be completed"
    assert reglages['mentions'] == {'rccm': '', 'nif': '', 'commerce_electronique': '', 'ipdcp': ''}
    assert reglages['en_formation'] is True
    assert reglages['contact_email']


def test_un_module_se_rallume_par_l_environnement(lancement):
    lancement.MODULES = {**lancement.MODULES, 'give': True}
    assert APIClient().get(SITE).json()['modules']['give'] is True


def test_numeros_legaux_depuis_l_environnement_puis_le_back_office(settings):
    settings.MENTIONS_LEGALES = {**settings.MENTIONS_LEGALES, 'ipdcp': 'D-2026-01'}
    ParametresSocieteModel.objects.create(rccm='TG-LFW-01-2026-B13-00001', nif='1000000001')
    mentions = APIClient().get(SITE).json()['mentions']
    assert mentions['ipdcp'] == 'D-2026-01'
    # RCCM and NIF: the environment variable wins; when empty, the back-office value is used
    assert mentions['rccm'] == 'TG-LFW-01-2026-B13-00001' and mentions['nif'] == '1000000001'
    settings.MENTIONS_LEGALES = {**settings.MENTIONS_LEGALES, 'rccm': 'RCCM-ENV'}
    assert APIClient().get(SITE).json()['mentions']['rccm'] == 'RCCM-ENV'


def test_societe_immatriculee_par_l_environnement(settings):
    # The day of the RCCM: SOCIETE_EN_FORMATION=False removes "en formation" from the site, without a code change
    settings.SOCIETE_EN_FORMATION = False
    assert APIClient().get(SITE).json()['en_formation'] is False


def test_un_commentaire_lu_comme_valeur_compte_comme_vide(monkeypatch):
    from config.settings import _mention

    # "SOCIETE_COMMERCE_ELECTRONIQUE=     # décret n° 2018-062/PR": the comment is never displayed
    monkeypatch.setenv('SOCIETE_COMMERCE_ELECTRONIQUE', '# décret n° 2018-062/PR')
    assert _mention('SOCIETE_COMMERCE_ELECTRONIQUE') == ''
    monkeypatch.setenv('SOCIETE_COMMERCE_ELECTRONIQUE', ' CE-2026-001 ')
    assert _mention('SOCIETE_COMMERCE_ELECTRONIQUE') == 'CE-2026-001'


def test_concierge_masque_aucune_requete_vers_gemini(lancement, make_user, monkeypatch):
    lancement.CONCIERGE = {**lancement.CONCIERGE, 'API_KEY': 'cle-test'}
    gemini = mock.Mock(side_effect=AssertionError('appel à Gemini'))
    monkeypatch.setattr(concierge, '_client', gemini)
    client = APIClient()
    assert client.get('/api/v1/concierge/statut/').json() == {'actif': False}
    client.force_authenticate(make_user())
    assert client.get('/api/v1/concierge/conversations/').status_code == 404
    assert client.post('/api/v1/concierge/conversations/').status_code == 404
    assert client.post('/api/v1/concierge/conversations/00000000-0000-0000-0000-000000000000/messages/',
                       {'texte': 'Bonjour'}, format='json').status_code == 404
    gemini.assert_not_called()


def test_moyens_de_paiement_non_ouverts_masques(lancement, make_user):
    lancement.FEDAPAY = {**lancement.FEDAPAY, 'SECRET_KEY': 'sk_test'}
    lancement.PAYPAL = {'CLIENT_ID': 'id', 'CLIENT_SECRET': 'secret', 'ENV': 'sandbox'}
    config = APIClient().get('/api/v1/paiements/config/').json()
    # Open: Moov Money (Flooz), Mixx by Yas (T-Money) and the card (Visa, Mastercard); not PayPal
    assert config['moyens'] == ['mobile_money', 'carte'] and not paiements.paypal_actif()
    assert config['pays'] == [{'code': 'TG', 'nom': 'Togo', 'indicatif': '228', 'chiffres': 8, 'operateurs': [
        {'code': 'moov_tg', 'nom': 'Moov Money (Flooz)'}, {'code': 'togocel', 'nom': 'Mixx by Yas (T-Money)'}]}]

    hote = APIClient()
    hote.force_authenticate(make_user(role='hote'))
    url = '/api/v1/paiements/profil-versement/'
    refuse = hote.put(url, {'pays': 'BJ', 'operateur': 'mtn_open', 'numero': '0197000000', 'titulaire': 'Ama'}, format='json')
    assert refuse.status_code == 400 and 'operateur' in refuse.json()
    accepte = hote.put(url, {'pays': 'TG', 'operateur': 'togocel', 'numero': '90000002', 'titulaire': 'Ama'}, format='json')
    assert accepte.status_code == 200

    # Switched back on by the switch, without a code change
    lancement.MODULES = {**lancement.MODULES, 'paiements_non_ouverts': True}
    config = APIClient().get('/api/v1/paiements/config/').json()
    assert 'paypal' in config['moyens'] and len(config['pays']) == 5
