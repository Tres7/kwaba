"""Rules of the ledger (domain, pure): which lines are refused, and the inverse line of a correction."""
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from apps.finance.domain.entities import ENTREE, SORTIE, Ecrivain, Ligne, Mouvement, Nature, Referentiels
from apps.finance.domain.exceptions import MouvementRefuse, RestitutionRefusee
from apps.finance.domain.rules import ecarts_des_modules_ouverts, inverse, mois_de, preparer, premier_du_mois

MAINTENANT = datetime(2026, 12, 20, 10, 0, tzinfo=timezone.utc)
HOTE = uuid.uuid4()
REF = Referentiels(
    natures={code: Nature(code, famille, sens, actif) for code, famille, sens, actif in [
        ('T01', 'T', None, True), ('R01', 'R', ENTREE, True), ('C01', 'C', ENTREE, True),
        ('C03', 'C', SORTIE, True), ('I01', 'I', ENTREE, False)]},
    offres={'COURTE_DUREE': True, 'EVENTS': False},
    comptes_argent={'FEDAPAY': True, 'BANQUE_EXP': False},
    tiers_types={'hote': True, 'bailleur': False},
    moyens_paiement={'MOOV': True},
)


def ligne(**champs) -> Ligne:
    valeurs = dict(nature='T01', offre='COURTE_DUREE', montant=250_000, sens=ENTREE, compte_argent='FEDAPAY',
                   tiers_type='hote', tiers_id=HOTE, moyen_paiement='MOOV')
    valeurs.update(champs)
    return Ligne(**valeurs)


def preparer_(ligne_):
    return preparer(ligne_, REF, origine='paiement', maintenant=MAINTENANT)


def test_a_valid_line_gets_its_month_and_clean_texts():
    ecriture = preparer_(ligne(piece_reference='  RES-1 ', externe_reference=' ', motif=''))

    assert ecriture.mois == date(2026, 12, 1)
    assert ecriture.date_evenement == MAINTENANT
    assert (ecriture.ligne.piece_reference, ecriture.ligne.externe_reference, ecriture.ligne.motif) == (
        'RES-1', None, None)


@pytest.mark.parametrize('champs, message', [
    ({'montant': 0}, 'positif'),
    ({'montant': -1}, 'positif'),
    ({'montant': 1999.98}, 'entier'),
    ({'montant': True}, 'entier'),
    ({'sens': 'debit'}, 'Sens'),
    ({'nature': 'Z99'}, 'inconnue'),
    ({'nature': 'I01', 'tiers_type': None, 'tiers_id': None}, 'inactive'),
    ({'nature': 'R01', 'sens': SORTIE, 'tiers_type': None, 'tiers_id': None}, 'attend le sens entree'),
    ({'offre': 'EVENTS'}, "n'est pas ouverte"),
    ({'offre': 'INCONNUE'}, 'inconnue'),
    ({'compte_argent': 'BANQUE_EXP'}, 'inactif'),
    ({'tiers_type': 'bailleur'}, 'inactif'),
    ({'moyen_paiement': 'PAYPAL'}, 'inconnu'),
    ({'tiers_id': None}, 'vont ensemble'),
    ({'tiers_type': None, 'tiers_id': None}, 'exige le tiers'),
    ({'nature': 'C01', 'tiers_type': None, 'tiers_id': None}, 'réservation ou la location'),
    ({'nature': 'C03', 'sens': SORTIE, 'tiers_type': None, 'tiers_id': None, 'location_id': uuid.uuid4()},
     'C03'),
    ({'date_evenement': datetime(2026, 12, 20, 10, 0)}, 'fuseau'),
])
def test_refused_lines(champs, message):
    with pytest.raises(MouvementRefuse, match=message):
        preparer_(ligne(**champs))


def test_the_accounting_month_is_the_utc_month_of_the_event():
    assert mois_de(datetime(2026, 12, 31, 23, 30, tzinfo=timezone(timedelta(hours=-2)))) == date(2027, 1, 1)
    with pytest.raises(RestitutionRefusee, match='premier jour'):
        premier_du_mois(date(2026, 12, 15))


def _ecrite() -> Mouvement:
    return Mouvement(id=7, ligne=ligne(), mois=date(2026, 11, 1), origine='paiement', annule_mouvement_id=None)


def test_the_inverse_line_mirrors_the_line_in_the_other_direction_today():
    ecriture = inverse(_ecrite(), motif=' Montant faux ', origine='correction', maintenant=MAINTENANT)

    assert ecriture.annule_mouvement_id == 7
    assert (ecriture.ligne.sens, ecriture.ligne.montant, ecriture.ligne.nature, ecriture.ligne.tiers_id) == (
        SORTIE, 250_000, 'T01', HOTE)
    assert (ecriture.mois, ecriture.ligne.motif) == (date(2026, 12, 1), 'Montant faux')


def test_a_correction_needs_a_reason_and_is_not_corrected_itself():
    with pytest.raises(MouvementRefuse, match='motif'):
        inverse(_ecrite(), motif='  ', origine='correction', maintenant=MAINTENANT)
    correction = Mouvement(id=8, ligne=ligne(sens=SORTIE), mois=date(2026, 12, 1), origine='correction',
                           annule_mouvement_id=7)
    with pytest.raises(MouvementRefuse, match='elle-même une correction'):
        inverse(correction, motif='Annuler', origine='correction', maintenant=MAINTENANT)


def test_open_modules_writing_to_inactive_codes_are_listed():
    ecrivains = [Ecrivain('sejours', frozenset({'COURTE_DUREE'}), frozenset({'T01', 'R01'})),
                 Ecrivain('sans_chauffeur', frozenset({'VOITURE_SANS'}), frozenset({'T03', 'R18'})),
                 Ecrivain('billetterie', frozenset({'EVENTS'}), frozenset({'T07'}), ouvert=lambda: False)]

    ecarts = ecarts_des_modules_ouverts(ecrivains, {'COURTE_DUREE'}, {'T01', 'R01', 'T03'})

    assert ecarts == ['Le module sans_chauffeur est ouvert mais écrirait dans : offre VOITURE_SANS, nature R18 '
                      '(inactive ou inconnue).']
