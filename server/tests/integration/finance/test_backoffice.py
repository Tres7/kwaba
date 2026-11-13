"""Back-office page « Grand livre » (section Finances): what it shows, and who may open it."""
import uuid

from apps.finance import api as finance

URL = '/api/v1/admin/finance/grand-livre/'


def _sejour_paye(hote):
    reservation = uuid.uuid4()
    commun = dict(offre='COURTE_DUREE', compte_argent='FEDAPAY', moyen_paiement='MOOV', reservation_id=reservation,
                  piece_reference='RES-TEST-0001', externe_reference='TX-1')
    finance.enregistrer([
        finance.Ligne(nature='T01', montant=250_000, sens=finance.ENTREE, tiers_type='hote', tiers_id=hote.pk, **commun),
        finance.Ligne(nature='T02', montant=15_000, sens=finance.ENTREE, tiers_type='hote', tiers_id=hote.pk, **commun),
        finance.Ligne(nature='R01', montant=15_000, sens=finance.ENTREE, **commun),
    ], origine='paiement')


def test_the_page_shows_the_invariants_the_three_balances_and_the_latest_lines(make_user, client_for):
    hote = make_user(role='hote', first_name='Ama', last_name='Mensah')
    _sejour_paye(hote)

    r = client_for(make_user(role='admin')).get(URL)

    assert r.status_code == 200
    d = r.json()
    assert {i['invariant'] for i in d['invariants']} == {'I5', 'I8', 'I9', 'I10', 'I11', 'I12', 'I13', 'I14'}
    assert d['soldes'] == {'revenu_du_mois': 15_000, 'du_partenaires': 265_000, 'du_voyageurs': 0,
                           'cautions_detenues': 0, 'comptes': {'FEDAPAY': 280_000}}
    assert d['du_aux_partenaires'] == [{'tiers_type': 'hote', 'tiers_id': str(hote.pk), 'nom': 'Ama Mensah',
                                        'email': hote.email, 'solde_du': 265_000}]
    assert [m['nature_code'] for m in d['mouvements']] == ['R01', 'T02', 'T01']
    assert d['mouvements'][2]['nom'] == 'Ama Mensah' and d['mouvements'][0]['montant_signe'] == 15_000


def test_only_the_admins_who_see_finances_open_it(make_user, client_for):
    assert client_for(make_user(role='admin', admin_sections=['documents', 'finances'])).get(URL).status_code == 200
    assert client_for(make_user(role='admin', admin_sections=['avis'])).get(URL).status_code == 403
    assert client_for(make_user(role='hote')).get(URL).status_code == 403
    assert client_for(make_user()).get(URL).status_code == 403
