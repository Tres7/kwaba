"""Reports of the ledger: the nine reference cases of the developers' prompt (03_Prompt, « au franc près »), the three
balances that never mix, double entry, invariants and the closing check. Series FA, FE and FH of the test plan.

The lines are written here by hand, as the payment module will write them (next PR): what is tested is that the
views of the schema give the expected figures from those lines."""
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.finance import api as finance
from apps.finance.models import CompteArgentModel, PeriodeModel, RapportModel, RapprochementJourModel

HOTE = str(uuid.uuid4())  # third party ids are text in the ledger
APPORTEUR = uuid.uuid4()


@dataclass(frozen=True)
class Cas:
    nom: str
    nuits: int
    frais_service: int
    menage: int
    commission: int
    frais_paiement: int
    # expected
    paye: int
    du: int
    revenu_brut: int
    revenu_net: int
    marge: int
    nature_commission: str = 'R02'
    tiers_type: str = 'hote'
    offre: str = 'COURTE_DUREE'
    apporteur: int = 0
    caution: int = 0
    moyen: str = 'MOOV'


# 03_Prompt_developpeurs_module_finance, « Valeurs de référence pour tes tests »
CAS = [
    Cas('particulier 8 %, ménage 15 000, Moov', 250_000, 15_000, 15_000, 20_000, 7_000,
        paye=280_000, du=245_000, revenu_brut=35_000, revenu_net=35_000, marge=28_000),
    Cas('hôtel 12 %, 3 nuits × 35 000', 105_000, 6_300, 0, 12_600, 2_782,
        paye=111_300, du=92_400, revenu_brut=18_900, revenu_net=18_900, marge=16_118,
        nature_commission='R03', tiers_type='hotel', offre='HOTEL'),
    Cas('hôte fondateur 5 %', 250_000, 15_000, 15_000, 12_500, 7_000,
        paye=280_000, du=252_500, revenu_brut=27_500, revenu_net=27_500, marge=20_500),
    Cas('apporté, apporteur 20 %', 250_000, 15_000, 15_000, 20_000, 7_000,
        paye=280_000, du=245_000, revenu_brut=35_000, revenu_net=28_000, marge=21_000, apporteur=7_000),
    Cas('entreprise, voyageur 4 %', 250_000, 10_000, 15_000, 20_000, 6_875,
        paye=275_000, du=245_000, revenu_brut=30_000, revenu_net=30_000, marge=23_125),
    Cas('client fidèle 3 %', 250_000, 7_500, 15_000, 20_000, 6_812,
        paye=272_500, du=245_000, revenu_brut=27_500, revenu_net=27_500, marge=20_688),
    Cas('caution formule c, 100 000', 250_000, 15_000, 15_000, 20_000, 9_500,
        paye=380_000, du=245_000, revenu_brut=35_000, revenu_net=35_000, marge=25_500, caution=100_000),
    Cas('paiement par carte 3,6 %', 250_000, 15_000, 15_000, 20_000, 10_080,
        paye=280_000, du=245_000, revenu_brut=35_000, revenu_net=35_000, marge=24_920, moyen='CARTE'),
    Cas('arrondi : nuits 33 333, ménage 4 000', 33_333, 2_000, 4_000, 2_667, 983,
        paye=39_333, du=34_666, revenu_brut=4_667, revenu_net=4_667, marge=3_684),
]


def sejour(cas: Cas, reservation=None, hote=HOTE, moment=None, ref='TX-1') -> uuid.UUID:
    """The lines of a paid stay, then of the arrival (commission acquired) and of the referrer's share."""
    reservation = reservation or uuid.uuid4()
    commun = dict(offre=cas.offre, compte_argent='FEDAPAY', moyen_paiement=cas.moyen, reservation_id=reservation,
                  piece_reference='RES-TEST', date_evenement=moment)
    tiers = dict(tiers_type=cas.tiers_type, tiers_id=hote)
    lignes = [finance.Ligne(nature='T01', montant=cas.nuits, sens=finance.ENTREE, externe_reference=ref,
                            **tiers, **commun),
              finance.Ligne(nature='R01', montant=cas.frais_service, sens=finance.ENTREE, externe_reference=ref,
                            **commun),
              finance.Ligne(nature='D01', montant=cas.frais_paiement, sens=finance.SORTIE, externe_reference=ref,
                            **commun)]
    if cas.menage:
        lignes.append(finance.Ligne(nature='T02', montant=cas.menage, sens=finance.ENTREE, externe_reference=ref,
                                    **tiers, **commun))
    if cas.caution:
        lignes.append(finance.Ligne(nature='C01', montant=cas.caution, sens=finance.ENTREE, externe_reference=ref,
                                    **commun))
    finance.enregistrer(lignes, origine='paiement')
    # At the arrival, the commission leaves the host's money for Kwa-Ba's (FIN-03, case FA-01)
    arrivee = [finance.Ligne(nature='T01', montant=cas.commission, sens=finance.SORTIE, **tiers, **commun),
               finance.Ligne(nature=cas.nature_commission, montant=cas.commission, sens=finance.ENTREE, **commun)]
    if cas.apporteur:
        arrivee.append(finance.Ligne(nature='D02', montant=cas.apporteur, sens=finance.SORTIE,
                                     tiers_type='apporteur', tiers_id=APPORTEUR, **commun))
    finance.enregistrer(arrivee, origine='arrivee')
    return reservation


def mois_courant() -> date:
    return finance.mois_de(timezone.now())


def somme(lignes) -> int:
    return sum(ligne['montant'] for ligne in lignes)


@pytest.mark.parametrize('cas', CAS, ids=[c.nom for c in CAS])
def test_reference_cases_to_the_franc(cas):
    sejour(cas)
    aujourdhui = timezone.now().date()

    # I1: collected = R + T + C lines (the commission moving from T to R at the arrival changes nothing)
    encaisse = somme(finance.synthese(aujourdhui, aujourdhui, 'famille', familles=['R', 'T', 'C']))
    du = {(r['tiers_type'], r['tiers_id']): r['solde_du'] for r in finance.du_aux_partenaires()}
    revenu_brut = somme(finance.synthese(aujourdhui, aujourdhui, 'nature', familles=['R']))
    cautions = sum(r['solde_detenu'] for r in finance.cautions_detenues())
    marge = {r['offre_code']: r for r in finance.marge_par_offre(mois_courant())}[cas.offre]

    assert encaisse == cas.paye
    assert du == {(cas.tiers_type, HOTE): cas.du}
    assert revenu_brut == cas.revenu_brut
    assert revenu_brut - cas.apporteur == cas.revenu_net
    assert marge['marge'] == cas.marge
    assert cautions == cas.caution
    # I2: total paid = owed to the partners + Kwa-Ba's revenue + deposits held
    assert cas.paye == cas.du + revenu_brut + cautions


def test_cleaning_fees_are_partner_money_never_revenue():
    """FA-12"""
    sejour(CAS[0])
    aujourdhui = timezone.now().date()

    recettes = {r['axe1']: r['montant'] for r in finance.synthese(aujourdhui, aujourdhui, 'nature', familles=['R'])}
    assert recettes == {'R01': 15_000, 'R02': 20_000}
    assert {r['axe1'] for r in finance.synthese(aujourdhui, aujourdhui, 'nature', familles=['T'])} == {'T01', 'T02'}


def test_three_balances_never_mix():
    """FE-11, FA-07, FE-08: revenue, money of the partners and deposits are three figures; returning the deposit
    brings what is held to zero and leaves the revenue untouched."""
    reservation = sejour(CAS[6])
    assert finance.cautions_detenues() == [{'reservation_id': reservation, 'location_id': None,
                                            'solde_detenu': 100_000}]

    finance.enregistrer([finance.Ligne(nature='C02', offre='COURTE_DUREE', montant=100_000, sens=finance.SORTIE,
                                       compte_argent='FEDAPAY', reservation_id=reservation)], origine='caution')

    aujourdhui = timezone.now().date()
    assert finance.cautions_detenues() == []
    assert somme(finance.synthese(aujourdhui, aujourdhui, 'nature', familles=['R'])) == 35_000
    assert finance.du_aux_partenaires()[0]['solde_du'] == 245_000


def test_balances_of_two_hosts_are_kept_apart():
    """FE-01: three bookings on two hosts give two balances."""
    autre = str(uuid.uuid4())
    sejour(CAS[0], ref='TX-A')
    sejour(CAS[0], ref='TX-B')
    sejour(CAS[1], hote=autre, ref='TX-C')

    du = {r['tiers_id']: r['solde_du'] for r in finance.du_aux_partenaires()}
    assert du == {HOTE: 490_000, autre: 92_400}


def test_reference_booking_balances_in_double_entry():
    """Note 12, section 8.4: the booking of 280 000, its fees, then the payout to the host. Each movement gives two
    lines of the same amount (FH-08), the host's account comes back to zero (FH-11), FedaPay keeps 28 000."""
    sejour(CAS[0])
    finance.enregistrer([finance.Ligne(nature='T09', offre='COURTE_DUREE', montant=245_000, sens=finance.SORTIE,
                                       compte_argent='FEDAPAY', tiers_type='hote', tiers_id=HOTE,
                                       externe_reference='PO-1')], origine='versement')

    lignes = finance.ecritures(mois_courant())
    par_mouvement = {}
    for ligne in lignes:
        par_mouvement.setdefault(ligne['mouvement_id'], []).append(ligne)
    for deux in par_mouvement.values():
        assert len(deux) == 2
        assert deux[0]['debit'] == deux[1]['credit'] and deux[0]['credit'] == deux[1]['debit']
    assert next(r for r in lignes if r['compte_general'] == '47121')['compte_auxiliaire'] == f'HOTE-{HOTE}'

    soldes = {r['compte_general']: r['solde'] for r in finance.balance_generale(mois_courant())}
    assert soldes == {'47121': 0, '554': 28_000, '6317': 7_000, '7061': -15_000, '7062': -20_000}
    assert finance.soldes_comptes_argent() == {'FEDAPAY': 28_000}
    assert [e['ecart'] for e in finance.controle_equilibre()] == [0]
    assert finance.du_aux_partenaires() == []
    assert {i['invariant']: i['anomalies'] for i in finance.controle_invariants()} == dict.fromkeys(
        ['I5', 'I8', 'I9', 'I10', 'I11', 'I12', 'I13', 'I14'], 0)


def test_internal_transfer_balances_account_585():
    """FH-13"""
    CompteArgentModel.objects.filter(code='BANQUE_FT').update(actif=True)
    sejour(CAS[0])
    commun = dict(nature='V01', offre='STRUCTURE', montant=200_000, externe_reference='VIR-1')
    finance.enregistrer([finance.Ligne(sens=finance.SORTIE, compte_argent='FEDAPAY', **commun),
                         finance.Ligne(sens=finance.ENTREE, compte_argent='BANQUE_FT', **commun)],
                        origine='virement')

    soldes = {r['compte_general']: r['solde'] for r in finance.balance_generale(mois_courant())}
    assert soldes['585'] == 0
    assert soldes['5212'] == 200_000
    assert finance.soldes_comptes_argent() == {'FEDAPAY': 273_000 - 200_000, 'BANQUE_FT': 200_000}


# --- Invariants and closing ---------------------------------------------------------------------------------------

def test_electronic_money_is_checked_on_its_cumulative_balance():
    """Collected in one month, paid out the next: the 554 account of the second month alone is in credit, the
    account itself never is. The file checked month by month and would have refused this sound month."""
    debut_du_mois = timezone.now().replace(day=1, hour=12, minute=0, second=0, microsecond=0)
    sejour(CAS[0], moment=debut_du_mois - timedelta(days=10))
    finance.enregistrer([finance.Ligne(nature='T09', offre='COURTE_DUREE', montant=245_000, sens=finance.SORTIE,
                                       compte_argent='FEDAPAY', tiers_type='hote', tiers_id=HOTE)],
                        origine='versement')

    assert {r['compte_general']: r['solde'] for r in finance.balance_generale(mois_courant())}['554'] == -245_000
    assert {i['invariant']: i['anomalies'] for i in finance.controle_invariants()}['I13'] == 0
    controles = {c['controle']: c['verdict'] for c in finance.peut_on_cloturer(mois_courant())}
    assert controles['Monnaie electronique non creditrice (55x)'] == 'OK'


def test_a_payout_without_receipt_makes_electronic_money_negative():
    """FH-16"""
    finance.enregistrer([finance.Ligne(nature='T09', offre='COURTE_DUREE', montant=50_000, sens=finance.SORTIE,
                                       compte_argent='FEDAPAY', tiers_type='hote', tiers_id=HOTE)],
                        origine='versement')

    assert {i['invariant']: i['anomalies'] for i in finance.controle_invariants()}['I13'] == 1
    controles = {c['controle']: c for c in finance.peut_on_cloturer(mois_courant())}
    assert controles['Monnaie electronique non creditrice (55x)']['verdict'] == 'REFUSE'


def test_a_day_without_reconciliation_is_never_a_zero_gap():
    """FIN-02.7 / FD-07: lines three days ago, nothing reconciled: three days in anomaly, until each one is done
    with a zero gap."""
    il_y_a_3_jours = timezone.now() - timedelta(days=3)
    sejour(CAS[0], moment=il_y_a_3_jours)
    assert {i['invariant']: i['anomalies'] for i in finance.controle_invariants()}['I5'] == 3

    for n in (3, 2, 1):
        RapprochementJourModel.objects.create(jour=(timezone.now() - timedelta(days=n)).date(),
                                              compte_argent_id='FEDAPAY', solde_livre=28_000, solde_externe=28_000,
                                              etat=RapprochementJourModel.FAIT)
    assert {i['invariant']: i['anomalies'] for i in finance.controle_invariants()}['I5'] == 0

    RapprochementJourModel.objects.filter(jour=(timezone.now() - timedelta(days=1)).date()).update(solde_externe=27_000)
    assert {i['invariant']: i['anomalies'] for i in finance.controle_invariants()}['I5'] == 1


def _mois_rapproche(mois: date) -> None:
    jour = mois
    while jour.month == mois.month:
        RapprochementJourModel.objects.create(jour=jour, compte_argent_id='FEDAPAY', solde_livre=0, solde_externe=0,
                                              etat=RapprochementJourModel.FAIT)
        jour += timedelta(days=1)


def test_a_sound_month_can_be_closed():
    """FH-17: last month, fully reconciled: the six checks are OK."""
    mois = (mois_courant() - timedelta(days=1)).replace(day=1)
    sejour(CAS[0], moment=timezone.now().replace(day=1) - timedelta(days=15))
    _mois_rapproche(mois)

    assert [c['verdict'] for c in finance.peut_on_cloturer(mois)] == ['OK'] * 6


def test_a_month_without_reconciliation_cannot_be_closed():
    mois = (mois_courant() - timedelta(days=1)).replace(day=1)
    sejour(CAS[0], moment=timezone.now().replace(day=1) - timedelta(days=15))

    controle = {c['controle']: c for c in finance.peut_on_cloturer(mois)}['Rapprochement du prestataire de paiement']
    assert controle['verdict'] == 'REFUSE' and 'jamais un ecart nul' in controle['que_faire']


def test_a_movement_without_account_blocks_the_closing():
    """FH-12, FH-18: the guarantee fund has no SYSCOHADA account yet (question to the chartered accountant)."""
    mois = (mois_courant() - timedelta(days=1)).replace(day=1)
    moment = timezone.now().replace(day=1) - timedelta(days=15)
    sejour(CAS[0], moment=moment)
    finance.enregistrer([finance.Ligne(nature='G01', offre='STRUCTURE', montant=1_750, sens=finance.SORTIE,
                                       compte_argent='FEDAPAY', date_evenement=moment)], origine='calcul')
    _mois_rapproche(mois)

    controles = {c['controle']: c for c in finance.peut_on_cloturer(mois)}
    assert controles['Mouvements sans compte SYSCOHADA']['verdict'] == 'REFUSE'
    assert controles['Mouvements sans compte SYSCOHADA']['que_faire'] != '—'
    assert {i['invariant']: i['anomalies'] for i in finance.controle_invariants()}['I12'] == 1


def test_closing_needs_the_first_day_of_a_month():
    with pytest.raises(ValueError, match='premier jour'):
        finance.peut_on_cloturer(date(2026, 12, 15))


def test_a_line_written_after_locking_is_counted():
    """I10: a line added to a month after it was locked (by-passing the trigger, e.g. restored from a backup)."""
    sejour(CAS[0])
    PeriodeModel.objects.filter(mois=mois_courant()).update(etat=PeriodeModel.VERROUILLEE,
                                                            verrouillee_le=timezone.now() - timedelta(days=1))
    assert {i['invariant']: i['anomalies'] for i in finance.controle_invariants()}['I10'] == 6


# --- Generic reports (FIN-17) -------------------------------------------------------------------------------------

def test_saved_reports_and_a_tenth_one_added_as_a_row():
    sejour(CAS[0])
    aujourdhui = timezone.now().date()

    recettes = finance.rapport('recettes_type', aujourdhui, aujourdhui)
    assert {(r['axe1'], r['axe2']): r['montant'] for r in recettes} == {
        ('R01', 'COURTE_DUREE'): 15_000, ('R02', 'COURTE_DUREE'): 20_000}

    RapportModel.objects.create(code='frais_par_moyen_et_offre', titre='Frais de paiement par moyen et par offre',
                                axe1_id='moyen', axe2_id='offre', familles=['D'])
    frais = finance.rapport('frais_par_moyen_et_offre', aujourdhui, aujourdhui)
    assert [(r['axe1'], r['axe2'], r['montant']) for r in frais] == [('MOOV', 'COURTE_DUREE', -7_000)]


@pytest.mark.parametrize('axe', ['inconnu', "mois'; DROP TABLE finance_mouvement; --"])
def test_an_unknown_axis_is_refused_with_a_message(axe):
    with pytest.raises(ValueError, match='axe inconnu'):
        finance.synthese(date(2026, 12, 1), date(2026, 12, 31), axe)
    assert finance.synthese(date(2026, 12, 1), date(2026, 12, 31)) == []
