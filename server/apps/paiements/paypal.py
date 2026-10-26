"""Minimal client of the PayPal Checkout API (v2 orders): https://developer.paypal.com/docs/api/orders/v2/

PayPal does not accept the CFA franc: the traveller pays in euros, at the fixed FCFA/euro
parity rate. The host is always paid in FCFA through FedaPay.
"""
import logging
import time
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.conf import settings

logger = logging.getLogger('apps.paiements.paypal')

URLS = {
    'sandbox': 'https://api-m.sandbox.paypal.com',
    'live': 'https://api-m.paypal.com',
}

FCFA_PAR_EURO = Decimal('655.957')  # fixed XOF/EUR parity

STATUTS_COMMANDE = {
    'COMPLETED': 'reussi',
    'VOIDED': 'annule',
}


class PayPalErreur(Exception):
    pass


def en_euros(montant_fcfa: int) -> Decimal:
    return (Decimal(montant_fcfa) / FCFA_PAR_EURO).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def id_capture(commande: dict) -> str:
    for unite in commande.get('purchase_units') or []:
        for capture in ((unite.get('payments') or {}).get('captures') or []):
            if capture.get('id'):
                return capture['id']
    return ''


class PayPal:
    _jeton: tuple[str, float] | None = None  # shared per process: (token, expiry)

    def __init__(self, client_id: str, secret: str, environnement: str = 'sandbox'):
        if not client_id or not secret:
            raise PayPalErreur("PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET ne sont pas configurés.")
        self.base = URLS.get(environnement, URLS['sandbox'])
        self.identifiants = (client_id, secret)

    def _jeton_acces(self) -> str:
        if PayPal._jeton and PayPal._jeton[1] > time.time() + 60:
            return PayPal._jeton[0]
        try:
            reponse = requests.post(
                f'{self.base}/v1/oauth2/token', auth=self.identifiants,
                data={'grant_type': 'client_credentials'}, timeout=20,
            )
        except requests.RequestException as exc:
            raise PayPalErreur(f"PayPal injoignable : {exc}") from exc
        if reponse.status_code >= 400:
            raise PayPalErreur("Identifiants PayPal refusés.")
        corps = reponse.json()
        PayPal._jeton = (corps['access_token'], time.time() + int(corps.get('expires_in', 300)))
        return PayPal._jeton[0]

    def _appel(self, methode: str, chemin: str, json: dict | None = None, idempotence: str = '') -> dict:
        entetes = {'Authorization': f'Bearer {self._jeton_acces()}', 'Content-Type': 'application/json'}
        if idempotence:
            entetes['PayPal-Request-Id'] = idempotence
        try:
            reponse = requests.request(methode, self.base + chemin, json=json, headers=entetes, timeout=20)
        except requests.RequestException as exc:
            raise PayPalErreur(f"PayPal injoignable : {exc}") from exc
        try:
            corps = reponse.json()
        except ValueError:
            corps = {}
        if reponse.status_code >= 400:
            details = corps.get('details') or [{}]
            message = details[0].get('issue') or corps.get('message') or reponse.text[:300]
            logger.warning("PayPal %s %s → %s : %s", methode, chemin, reponse.status_code, message)
            raise PayPalErreur(str(message))
        return corps

    def creer_commande(self, *, montant_eur: Decimal, description: str, reference: str,
                       url_retour: str, url_annulation: str) -> tuple[str, str]:
        """Returns (order id, address where the traveller approves the payment)."""
        commande = self._appel('POST', '/v2/checkout/orders', {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': reference,
                'description': description[:127],
                'amount': {'currency_code': 'EUR', 'value': str(montant_eur)},
            }],
            'payment_source': {'paypal': {'experience_context': {
                'brand_name': 'Kwa-Ba',
                'locale': 'fr-FR',
                'shipping_preference': 'NO_SHIPPING',
                'user_action': 'PAY_NOW',
                'return_url': url_retour,
                'cancel_url': url_annulation,
            }}},
        }, idempotence=reference)
        lien = next((lk['href'] for lk in commande.get('links', []) if lk.get('rel') in ('payer-action', 'approve')), '')
        if not lien:
            raise PayPalErreur("PayPal n'a pas renvoyé de lien de paiement.")
        return commande['id'], lien

    def lire_commande(self, identifiant: str) -> dict:
        return self._appel('GET', f'/v2/checkout/orders/{identifiant}')

    def capturer(self, identifiant: str) -> dict:
        """Captures an order approved by the traveller (idempotent on PayPal's side)."""
        return self._appel('POST', f'/v2/checkout/orders/{identifiant}/capture', {}, idempotence=f'capture-{identifiant}')

    def rembourser(self, capture: str, montant_eur: Decimal, reference: str) -> dict:
        return self._appel('POST', f'/v2/payments/captures/{capture}/refund', {
            'amount': {'currency_code': 'EUR', 'value': str(montant_eur)},
        }, idempotence=reference)

    def lire_remboursement(self, identifiant: str) -> dict:
        return self._appel('GET', f'/v2/payments/refunds/{identifiant}')


def client() -> PayPal:
    return PayPal(settings.PAYPAL['CLIENT_ID'], settings.PAYPAL['CLIENT_SECRET'], settings.PAYPAL['ENV'])
