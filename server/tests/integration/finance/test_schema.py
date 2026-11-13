"""The SQL part of the module (ADR-024): triggers, reporting views and functions exist and answer, the views are
dropped before a migration and created again after it, and an open module that would write to an inactive offer or
nature stops the deployment (check finance.E001) and shows on the control screen (I14)."""
import pytest
from django.db import connection

from apps.finance import api as finance
from apps.finance.application.registre import ECRIVAINS
from apps.finance.infrastructure.checks import modules_ouverts_et_referentiel
from apps.finance.infrastructure.persistence import sql_restitutions

VUES = ['finance_mouvement_signe', 'finance_recettes_par_type', 'finance_depenses_par_type', 'finance_marge_par_offre',
        'finance_du_aux_partenaires', 'finance_cautions_detenues', 'finance_solde_compte_argent',
        'finance_taux_frais_reel', 'finance_ecriture', 'finance_export_comptable', 'finance_livre_journal',
        'finance_grand_livre', 'finance_balance_generale', 'finance_controle_equilibre',
        'finance_ecritures_sans_compte', 'finance_controle_invariants', 'finance_pivot']
FONCTIONS = ['finance_peut_on_cloturer', 'finance_synthese', 'finance_mouvement_ajout_seul',
             'finance_historique_ajout_seul', 'finance_mouvement_controles']
TRIGGERS = ['trg_finance_mouvement_ajout_seul', 'trg_finance_mouvement_controles',
            'trg_finance_parametre_histo_ajout_seul', 'trg_finance_correspondance_histo_ajout_seul']


def _noms(sql: str) -> set[str]:
    with connection.cursor() as curseur:
        curseur.execute(sql)
        return {ligne[0] for ligne in curseur.fetchall()}


def _vues() -> set[str]:
    return _noms("SELECT viewname FROM pg_views WHERE viewname LIKE 'finance\\_%'")


def test_every_view_function_and_trigger_of_the_schema_exists_and_answers():
    assert _vues() == set(VUES)
    assert set(FONCTIONS) <= _noms("SELECT proname FROM pg_proc WHERE proname LIKE 'finance\\_%'")
    assert set(TRIGGERS) <= _noms("SELECT tgname FROM pg_trigger WHERE tgname LIKE 'trg_finance\\_%'")
    with connection.cursor() as curseur:
        for vue in VUES:
            curseur.execute(f'SELECT * FROM {vue} LIMIT 0')


def test_views_are_dropped_before_a_migration_and_created_again_after():
    """A migration can change a column of the ledger: no view stands in its way, and the views of the code come
    back afterwards."""
    sql_restitutions.avant_migration(sender=None)
    assert _vues() == set()

    sql_restitutions.apres_migration(sender=None)
    sql_restitutions.apres_migration(sender=None)  # twice: no harm

    assert _vues() == set(VUES)
    assert {i['invariant'] for i in finance.controle_invariants()} >= {'I5', 'I13'}


@pytest.fixture
def module_sans_chauffeur(monkeypatch):
    """A module that writes the car rental without driver (offer VOITURE_SANS, inactive: wave 3)."""
    ouvert = {'valeur': True}
    monkeypatch.setitem(ECRIVAINS, 'location_sans_chauffeur', None)
    finance.declarer_ecritures('location_sans_chauffeur', offres={'VOITURE_SANS'}, natures={'T03', 'R05', 'C01'},
                               ouvert=lambda: ouvert['valeur'])
    return ouvert


def test_an_open_module_writing_to_an_inactive_offer_stops_the_deployment(module_sans_chauffeur):
    erreurs = modules_ouverts_et_referentiel(databases=['default'])

    assert [e.id for e in erreurs] == ['finance.E001']
    assert 'location_sans_chauffeur' in erreurs[0].msg and 'offre VOITURE_SANS' in erreurs[0].msg
    assert {i['invariant']: i['anomalies'] for i in finance.controle_invariants()}['I14'] == 1


def test_the_same_module_closed_is_fine(module_sans_chauffeur):
    module_sans_chauffeur['valeur'] = False

    assert modules_ouverts_et_referentiel(databases=['default']) == []
    assert {i['invariant']: i['anomalies'] for i in finance.controle_invariants()}['I14'] == 0


def test_the_check_needs_the_database(module_sans_chauffeur):
    """Without --database (plain `manage.py check`), it reads nothing."""
    assert modules_ouverts_et_referentiel(databases=None) == []
