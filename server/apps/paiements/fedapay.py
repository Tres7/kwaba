"""Minimal client of the FedaPay API (https://docs.fedapay.com).

Only this module talks to FedaPay: changing provider (Ghana, English-speaking countries…) means
writing another client exposing the same methods.
"""
import hashlib
import hmac
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger('apps.paiements.fedapay')

URLS = {
    'sandbox': 'https://sandbox-api.fedapay.com/v1',
    'live': 'https://api.fedapay.com/v1',
}

# Statuts FedaPay → statuts internes
STATUTS_TRANSACTION = {
    'approved': 'reussi',
    'transferred': 'reussi',
    'declined': 'echoue',
    'canceled': 'annule',
    'cancelled': 'annule',
    'refunded': 'annule',
    'expired': 'annule',
}
STATUTS_PAYOUT = {
    'sent': 'envoye',
    'failed': 'echoue',
}


class FedaPayErreur(Exception):
    pass


def _objet(corps: dict, nom: str) -> dict:
    """FedaPay responses wrap the object: {"v1/transaction": {...}}."""
    for cle in (f'v1/{nom}', nom):
        if isinstance(corps.get(cle), dict):
            return corps[cle]
    return corps


class FedaPay:
    def __init__(self, cle_secrete: str, environnement: str = 'sandbox'):
        if not cle_secrete:
            raise FedaPayErreur("FEDAPAY_SECRET_KEY n'est pas configurée.")
        self.base = URLS.get(environnement, URLS['sandbox'])
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {cle_secrete}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

    def _appel(self, methode: str, chemin: str, json: dict | None = None) -> dict:
        try:
            reponse = self.session.request(methode, self.base + chemin, json=json, timeout=20)
        except requests.RequestException as exc:
            raise FedaPayErreur(f"FedaPay injoignable : {exc}") from exc
        try:
            corps = reponse.json()
        except ValueError:
            corps = {}
        if reponse.status_code >= 400:
            message = corps.get('message') or corps.get('errors') or reponse.text[:300]
            logger.warning("FedaPay %s %s → %s : %s", methode, chemin, reponse.status_code, message)
            raise FedaPayErreur(str(message))
        return corps

    # --- Encaissement ---------------------------------------------------------------

    def creer_transaction(self, *, montant: int, description: str, callback_url: str, client: dict) -> tuple[str, str]:
        """Creates the transaction and its payment link. Returns (id, url of the payment page)."""
        transaction = _objet(self._appel('POST', '/transactions', {
            'description': description[:255],
            'amount': montant,
            'currency': {'iso': 'XOF'},
            'callback_url': callback_url,
            'customer': client,
        }), 'transaction')
        identifiant = str(transaction['id'])
        jeton = self._appel('POST', f'/transactions/{identifiant}/token')
        return identifiant, jeton['url']

    def lire_transaction(self, identifiant: str) -> dict:
        return _objet(self._appel('GET', f'/transactions/{identifiant}'), 'transaction')

    # --- Versements (payouts) -------------------------------------------------------

    def creer_versement(self, *, montant: int, mode: str, client: dict) -> str:
        """Creates then starts a Mobile Money payout. Returns the payout id."""
        payout = _objet(self._appel('POST', '/payouts', {
            'amount': montant,
            'currency': {'iso': 'XOF'},
            'mode': mode,
            'customer': client,
        }), 'payout')
        identifiant = str(payout['id'])
        self._appel('PUT', '/payouts/start', {'payouts': [{'id': identifiant}]})
        return identifiant

    def lire_versement(self, identifiant: str) -> dict:
        return _objet(self._appel('GET', f'/payouts/{identifiant}'), 'payout')


def client() -> FedaPay:
    return FedaPay(settings.FEDAPAY['SECRET_KEY'], settings.FEDAPAY['ENV'])


def signature_valide(corps: bytes, entete: str, secret: str, tolerance: int = 300) -> bool:
    """Checks the X-FEDAPAY-SIGNATURE header ("t=<timestamp>,s=<hmac sha256>")."""
    elements = dict(
        morceau.split('=', 1) for morceau in (entete or '').split(',') if '=' in morceau
    )
    horodatage, signature = elements.get('t'), elements.get('s')
    if not horodatage or not signature:
        return False
    try:
        if abs(time.time() - int(horodatage)) > tolerance:
            return False
    except ValueError:
        return False
    attendu = hmac.new(secret.encode(), f"{horodatage}.".encode() + corps, hashlib.sha256).hexdigest()
    return hmac.compare_digest(attendu, signature)
