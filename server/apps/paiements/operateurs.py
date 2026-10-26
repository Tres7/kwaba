"""Countries open to payment and Mobile Money operators usable for payouts to hosts.

`mode` = id of the payout method at FedaPay. To check in the FedaPay dashboard
(Settings → Payment methods / Payouts) before going live: a mode not enabled on the account
is refused by the API, and the payout then fails with FedaPay's message (visible in the
Django admin).

At launch, only Moov Money (Flooz) and Mixx by Yas (T-Money) are open: the other operators stay
defined here but are only offered if the MODULE_PAIEMENTS_NON_OUVERTS switch is on (config/site.py).
"""
from django.conf import settings

PAYS = {
    'TG': {'nom': 'Togo', 'indicatif': '228', 'chiffres': 8, 'operateurs': [
        ('moov_tg', 'Moov Money (Flooz)'),
        ('togocel', 'Mixx by Yas (T-Money)'),
    ]},
    'BJ': {'nom': 'Bénin', 'indicatif': '229', 'chiffres': 10, 'operateurs': [
        ('mtn_open', 'MTN Mobile Money'),
        ('moov', 'Moov Money'),
        ('sbin', 'Celtiis Cash'),
    ]},
    'BF': {'nom': 'Burkina Faso', 'indicatif': '226', 'chiffres': 8, 'operateurs': [
        ('orange_bf', 'Orange Money'),
        ('moov_bf', 'Moov Money'),
    ]},
    'NE': {'nom': 'Niger', 'indicatif': '227', 'chiffres': 8, 'operateurs': [
        ('airtel_ne', 'Airtel Money'),
    ]},
    'ML': {'nom': 'Mali', 'indicatif': '223', 'chiffres': 8, 'operateurs': [
        ('orange_ml', 'Orange Money'),
        ('moov_ml', 'Moov Money'),
    ]},
}

PAYS_CHOICES = [(code, p['nom']) for code, p in PAYS.items()]
OPERATEUR_CHOICES = [op for p in PAYS.values() for op in p['operateurs']]


OUVERTS = {'moov_tg', 'togocel'}


def pays_ouverts() -> dict:
    """Countries and operators offered to users (refund, host payout)."""
    if settings.MODULES['paiements_non_ouverts']:
        return PAYS
    ouverts = {code: {**p, 'operateurs': [op for op in p['operateurs'] if op[0] in OUVERTS]} for code, p in PAYS.items()}
    return {code: p for code, p in ouverts.items() if p['operateurs']}


def operateurs_du_pays(pays: str) -> dict[str, str]:
    """All operators of the country (payouts to partners entered by the team in the back-office)."""
    return dict(PAYS.get(pays, {}).get('operateurs', []))


def operateurs_ouverts(pays: str) -> dict[str, str]:
    """Operators offered to users (refund number, host payout account)."""
    return dict(pays_ouverts().get(pays, {}).get('operateurs', []))


def nom_operateur(mode: str) -> str:
    return dict(OPERATEUR_CHOICES).get(mode, mode)
