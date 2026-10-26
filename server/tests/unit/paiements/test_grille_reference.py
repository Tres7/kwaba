"""Reference cases of the price grid (traveller fees 6 % or 3 %, host commission 8, 5 or 12 %)."""
from datetime import date

import pytest

from apps.paiements import tarifs
from apps.paiements.models import ConditionsHoteModel

PARTICULIER, FONDATEUR, HOTEL = tarifs.COMMISSION_PARTICULIER, tarifs.COMMISSION_FONDATEUR, tarifs.COMMISSION_HOTEL
NORMAL, FIDELE = tarifs.FRAIS_VOYAGEUR, tarifs.FRAIS_REDUITS


@pytest.mark.parametrize('nuits, frais, commission, total, commission_hote, revenu_hote, revenu_kwaba', [
    (1, NORMAL, PARTICULIER, 106000, 8000, 92000, 14000),   # Particulier, 1 nuit
    (1, NORMAL, FONDATEUR, 106000, 5000, 95000, 11000),     # Fondateur, 1 nuit
    (1, NORMAL, HOTEL, 106000, 12000, 88000, 18000),        # Hotel, 1 night
    (2, NORMAL, PARTICULIER, 212000, 16000, 184000, 28000),  # Particulier, 2 nuits
    (1, FIDELE, PARTICULIER, 103000, 8000, 92000, 11000),   # Individual, loyal customer, 1 night
])
def test_tableau_de_reference(nuits, frais, commission, total, commission_hote, revenu_hote, revenu_kwaba):
    m = tarifs.calculer(100000, nuits, frais=frais, commission=commission)
    assert (m.total, m.commission_hote, m.montant_hote, m.revenu_kwaba) == (total, commission_hote, revenu_hote, revenu_kwaba)
    # The host's gross price is never changed: the traveller's fees are not taken from their income
    assert m.prix_nuits == 100000 * nuits and m.montant_hote == m.prix_nuits - m.commission_hote


@pytest.mark.parametrize('nuits, sous_total, frais, total, commission, revenu', [
    (1, 100000, 6000, 106000, 8000, 92000),
    (2, 200000, 12000, 212000, 16000, 184000),
    (3, 300000, 18000, 318000, 24000, 276000),
    (5, 500000, 30000, 530000, 40000, 460000),
])
def test_sejours_de_plusieurs_nuits(nuits, sous_total, frais, total, commission, revenu):
    m = tarifs.calculer(100000, nuits)
    assert (m.prix_nuits, m.frais_service, m.total, m.commission_hote, m.montant_hote) == (sous_total, frais, total, commission, revenu)


@pytest.mark.parametrize('prix, nuits', [(0, 1), (-100000, 1), (100000, 0), (100000, -2), (100000, 1.5)])
def test_entrees_invalides_refusees(prix, nuits):
    with pytest.raises(ValueError):
        tarifs.calculer(prix, nuits)


def test_fondateur_a_5_pour_cent_pendant_6_mois_puis_8(monkeypatch):
    conditions = ConditionsHoteModel(categorie='particulier', fondateur_debut=date(2026, 11, 1), fondateur_fin=date(2027, 4, 30))
    monkeypatch.setattr(tarifs, 'conditions', lambda hote: conditions)
    assert tarifs.taux_commission(None, date(2026, 11, 1)) == FONDATEUR
    assert tarifs.taux_commission(None, date(2027, 4, 30)) == FONDATEUR
    assert tarifs.taux_commission(None, date(2027, 5, 1)) == PARTICULIER  # after the six months
    assert tarifs.taux_commission(None, date(2026, 10, 31)) == PARTICULIER  # before the programme


def test_compte_sans_conditions_n_est_pas_fondateur(monkeypatch):
    monkeypatch.setattr(tarifs, 'conditions', lambda hote: None)
    assert tarifs.taux_commission(None, date(2026, 11, 1)) == PARTICULIER
