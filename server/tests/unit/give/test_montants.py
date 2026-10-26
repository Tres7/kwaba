"""Kwa-Ba Give: fees chosen by the donor and transfer schedule."""
from datetime import date

import pytest

from apps.give import montants


@pytest.mark.parametrize('montant, couvre, attendu', [
    (2000, True, (62, 2062, 2000)),  # the NGO receives everything, the donor adds the fees
    (2000, False, (60, 2000, 1940)),  # fees deducted from the donation
    (500, True, (16, 516, 500)),
    (1950, False, (59, 1950, 1891)),  # 58.5 rounded up, like on the site
])
def test_calculer(montant, couvre, attendu):
    m = montants.calculer(montant, couvre)
    assert (m.frais, m.total, m.montant_ong) == attendu
    assert m.don == montant


def test_calendrier():
    assert montants.debut_du_mois(date(2026, 10, 25)) == date(2026, 10, 1)
    assert montants.mois_suivant(date(2026, 12, 3)) == date(2027, 1, 1)
    assert montants.date_reversement(date(2026, 10, 31)) == date(2026, 11, montants.JOUR_REVERSEMENT)
    assert montants.date_reversement(date(2026, 12, 1)) == date(2027, 1, montants.JOUR_REVERSEMENT)


def test_aucune_commission_au_lancement():
    assert montants.COMMISSION_KWABA == 0
    assert montants.MONTANTS_SUGGERES == [500, 2000, 3000, 5000]
