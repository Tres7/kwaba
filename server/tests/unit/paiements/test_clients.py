"""FedaPay and PayPal clients: requests sent and responses read (simulated HTTP)."""
import hashlib
import hmac
import time
from decimal import Decimal
from unittest import mock

import pytest
import requests

from apps.paiements import fedapay, paypal


def _reponse(status=200, corps=None, texte=''):
    r = mock.Mock(status_code=status, text=texte)
    if corps is None:
        r.json.side_effect = ValueError
    else:
        r.json.return_value = corps
    return r


# --- FedaPay ------------------------------------------------------------------------------

def test_fedapay_sans_cle():
    with pytest.raises(fedapay.FedaPayErreur):
        fedapay.FedaPay('')


def test_fedapay_transaction_puis_jeton():
    client = fedapay.FedaPay('sk_sandbox_x', 'sandbox')
    client.session.request = mock.Mock(side_effect=[
        _reponse(corps={'v1/transaction': {'id': 42}}),
        _reponse(corps={'token': 't', 'url': 'https://sandbox-process.fedapay.com/t'}),
    ])
    identifiant, url = client.creer_transaction(montant=10800, description='x' * 300, callback_url='http://cb', client={'email': 'a@b.c'})
    assert (identifiant, url) == ('42', 'https://sandbox-process.fedapay.com/t')
    methode, adresse = client.session.request.call_args_list[0].args
    assert (methode, adresse) == ('POST', 'https://sandbox-api.fedapay.com/v1/transactions')
    envoye = client.session.request.call_args_list[0].kwargs['json']
    assert envoye['currency'] == {'iso': 'XOF'} and len(envoye['description']) == 255
    assert client.session.headers['Authorization'] == 'Bearer sk_sandbox_x'


def test_fedapay_lectures_et_versement():
    client = fedapay.FedaPay('sk_live_x', 'live')
    assert client.base == 'https://api.fedapay.com/v1'
    client.session.request = mock.Mock(side_effect=[
        _reponse(corps={'v1/transaction': {'id': 1, 'status': 'approved'}}),
        _reponse(corps={'v1/payout': {'id': 9}}),
        _reponse(corps={}),
        _reponse(corps={'payout': {'id': 9, 'status': 'sent'}}),
    ])
    assert client.lire_transaction('1')['status'] == 'approved'
    assert client.creer_versement(montant=5000, mode='togocel', client={}) == '9'
    assert client.session.request.call_args_list[2].kwargs['json'] == {'payouts': [{'id': '9'}]}
    assert client.lire_versement('9')['status'] == 'sent'


def test_fedapay_erreurs():
    client = fedapay.FedaPay('sk_sandbox_x')
    client.session.request = mock.Mock(return_value=_reponse(403, {'message': 'Opération non autorisée'}))
    with pytest.raises(fedapay.FedaPayErreur, match='non autorisée'):
        client.lire_versement('1')
    client.session.request = mock.Mock(return_value=_reponse(500, None, 'panne'))
    with pytest.raises(fedapay.FedaPayErreur, match='panne'):
        client.lire_transaction('1')
    client.session.request = mock.Mock(side_effect=requests.ConnectionError('réseau'))
    with pytest.raises(fedapay.FedaPayErreur, match='injoignable'):
        client.lire_transaction('1')


def test_fedapay_client_depuis_les_reglages(settings):
    settings.FEDAPAY = {**settings.FEDAPAY, 'SECRET_KEY': 'sk_sandbox_y', 'ENV': 'sandbox'}
    assert isinstance(fedapay.client(), fedapay.FedaPay)


def test_signature_webhook():
    corps = b'{"name":"transaction.approved"}'
    t = str(int(time.time()))
    s = hmac.new(b'secret', f'{t}.'.encode() + corps, hashlib.sha256).hexdigest()
    assert fedapay.signature_valide(corps, f't={t},s={s}', 'secret')
    assert not fedapay.signature_valide(corps, f't={t},s=faux', 'secret')
    assert not fedapay.signature_valide(corps, '', 'secret')
    assert not fedapay.signature_valide(corps, 't=abc,s=x', 'secret')
    assert not fedapay.signature_valide(corps, f't={int(t) - 1000},s={s}', 'secret')  # trop ancien


# --- PayPal -------------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _jeton_vide():
    paypal.PayPal._jeton = None
    yield
    paypal.PayPal._jeton = None


def test_paypal_sans_identifiants():
    with pytest.raises(paypal.PayPalErreur):
        paypal.PayPal('', '')


def test_paypal_commande_capture_remboursement():
    client = paypal.PayPal('id', 'secret', 'live')
    assert client.base == 'https://api-m.paypal.com'
    with mock.patch.object(paypal.requests, 'post', return_value=_reponse(corps={'access_token': 'jeton', 'expires_in': 3600})) as post, \
         mock.patch.object(paypal.requests, 'request', side_effect=[
             _reponse(201, {'id': 'O1', 'links': [{'rel': 'self', 'href': 'x'}, {'rel': 'payer-action', 'href': 'https://paypal/payer'}]}),
             _reponse(corps={'id': 'O1', 'status': 'APPROVED'}),
             _reponse(corps={'id': 'O1', 'status': 'COMPLETED', 'purchase_units': [{'payments': {'captures': [{'id': 'CAP'}]}}]}),
             _reponse(corps={'id': 'R1', 'status': 'COMPLETED'}),
             _reponse(corps={'id': 'R1', 'status': 'COMPLETED'}),
         ]) as req:
        assert client.creer_commande(montant_eur=Decimal('16.46'), description='Séjour', reference='ref',
                                     url_retour='http://r', url_annulation='http://a') == ('O1', 'https://paypal/payer')
        assert client.lire_commande('O1')['status'] == 'APPROVED'
        assert paypal.id_capture(client.capturer('O1')) == 'CAP'
        assert client.rembourser('CAP', Decimal('10.00'), 'remb')['status'] == 'COMPLETED'
        assert client.lire_remboursement('R1')['id'] == 'R1'
    assert post.call_count == 1  # token reused while it is valid
    entetes = req.call_args_list[0].kwargs['headers']
    assert entetes['Authorization'] == 'Bearer jeton' and entetes['PayPal-Request-Id'] == 'ref'
    assert req.call_args_list[0].kwargs['json']['purchase_units'][0]['amount'] == {'currency_code': 'EUR', 'value': '16.46'}


def test_paypal_erreurs():
    client = paypal.PayPal('id', 'secret')
    with mock.patch.object(paypal.requests, 'post', return_value=_reponse(401, {})):
        with pytest.raises(paypal.PayPalErreur, match='refusés'):
            client.lire_commande('O1')
    with mock.patch.object(paypal.requests, 'post', side_effect=requests.Timeout('lent')):
        with pytest.raises(paypal.PayPalErreur, match='injoignable'):
            client.lire_commande('O1')
    paypal.PayPal._jeton = ('jeton', time.time() + 3600)
    with mock.patch.object(paypal.requests, 'request', return_value=_reponse(422, {'details': [{'issue': 'ORDER_NOT_APPROVED'}]})):
        with pytest.raises(paypal.PayPalErreur, match='ORDER_NOT_APPROVED'):
            client.capturer('O1')
    with mock.patch.object(paypal.requests, 'request', side_effect=requests.ConnectionError('réseau')):
        with pytest.raises(paypal.PayPalErreur, match='injoignable'):
            client.lire_commande('O1')
    with mock.patch.object(paypal.requests, 'request', return_value=_reponse(201, {'id': 'O2', 'links': []})):
        with pytest.raises(paypal.PayPalErreur, match='lien'):
            client.creer_commande(montant_eur=Decimal('1'), description='d', reference='r', url_retour='u', url_annulation='a')


def test_paypal_outils(settings):
    assert paypal.en_euros(655957) == Decimal('1000.00')
    assert paypal.id_capture({'purchase_units': [{'payments': {}}]}) == ''
    settings.PAYPAL = {'CLIENT_ID': 'i', 'CLIENT_SECRET': 's', 'ENV': 'sandbox'}
    assert isinstance(paypal.client(), paypal.PayPal)
