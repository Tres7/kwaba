"""Ledger of money movements (FIN-01): reference data, writing, refusals by the application AND by the database,
idempotence, corrections by inverse lines. Cases of series FB of the finance audit test plan (04_Plan_de_test)."""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.finance import api as finance
from apps.finance.models import (CompteArgentModel, CorrespondanceHistoModel, MouvementModel, NatureModel,
                                 OffreModel, ParametreHistoModel, ParametreModel, PeriodeModel, RapportModel)
from apps.activity.models import ActivityEntryModel

HOTE = str(uuid.uuid4())  # third party ids are text in the ledger
RESERVATION = uuid.uuid4()


@pytest.fixture
def admin_finance(make_user):
    return make_user(role='admin')


def ligne(**champs) -> finance.Ligne:
    valeurs = dict(nature='T01', offre='COURTE_DUREE', montant=250_000, sens=finance.ENTREE, compte_argent='FEDAPAY',
                   tiers_type='hote', tiers_id=HOTE, moyen_paiement='MOOV', reservation_id=RESERVATION,
                   piece_reference='RES-TEST-0001')
    valeurs.update(champs)
    return finance.Ligne(**valeurs)


def inserer_brut(**champs) -> int:
    """INSERT straight into the table, as a script or psql would: only the database guards stand in the way."""
    moment = champs.pop('date_evenement', timezone.now())
    valeurs = {'date_evenement': moment, 'mois_comptable': finance.mois_de(moment), 'montant': 1_000,
               'sens': 'entree', 'nature_code': 'R01', 'offre_code': 'COURTE_DUREE', 'compte_argent_code': 'FEDAPAY',
               'origine': 'script'}
    valeurs.update(champs)
    PeriodeModel.objects.get_or_create(mois=valeurs['mois_comptable'])
    colonnes = ', '.join([*valeurs, 'metadonnees'])
    with transaction.atomic(), connection.cursor() as curseur:
        curseur.execute(f"INSERT INTO finance_mouvement ({colonnes}) VALUES ({', '.join(['%s'] * len(valeurs))}, "
                        "'{}'::jsonb) RETURNING id", list(valeurs.values()))
        return curseur.fetchone()[0]


def executer(sql: str, params=()):
    with transaction.atomic(), connection.cursor() as curseur:
        curseur.execute(sql, params)


# --- Reference data -----------------------------------------------------------------------------------------------

def test_reference_data_of_the_schema_is_loaded():
    assert NatureModel.objects.count() == 54
    assert NatureModel.objects.filter(actif=True).count() == 40
    assert ParametreModel.objects.count() == 95
    assert ParametreModel.objects.filter(actif=True).count() == 53
    assert OffreModel.objects.filter(active=True).count() == 6
    assert RapportModel.objects.count() == 9
    assert list(CompteArgentModel.objects.filter(actif=True).values_list('code', flat=True)) == ['FEDAPAY']
    # Values waiting for a decision of the partners are at zero: the rule produces no amount
    for cle in ('fonds_garantie_taux', 'double_validation_seuil', 'garantie_renforcee_beneficiaire'):
        assert finance.parametre(cle) == 0


def test_parametre_reads_an_active_value_and_refuses_unknown_or_inactive_keys():
    assert finance.parametre('frais_service_voyageur') == Decimal('6')
    with pytest.raises(ValueError, match='inconnu'):
        finance.parametre('taux_invente')
    with pytest.raises(ValueError, match='inactif'):
        finance.parametre('events_commission')


# --- Writing --------------------------------------------------------------------------------------------------------

def test_a_payment_writes_one_line_per_nature_with_all_its_axes():
    ids = finance.enregistrer([ligne(externe_reference='TX-1'),
                               ligne(nature='T02', montant=15_000, externe_reference='TX-1'),
                               ligne(nature='R01', montant=15_000, tiers_type=None, tiers_id=None,
                                     externe_reference='TX-1')], origine='paiement')

    assert len(ids) == 3
    t01 = MouvementModel.objects.get(pk=ids[0])
    assert (t01.nature_id, t01.offre_id, t01.tiers_type_id, t01.tiers_id, t01.moyen_paiement_id,
            t01.compte_argent_id, t01.piece_reference, t01.reservation_id, t01.devise) == (
        'T01', 'COURTE_DUREE', 'hote', HOTE, 'MOOV', 'FEDAPAY', 'RES-TEST-0001', RESERVATION, 'XOF')
    assert t01.periode_id == timezone.now().date().replace(day=1)
    assert t01.cree_le is not None and t01.origine == 'paiement'


def test_an_action_that_fails_after_its_lines_leaves_none():
    """FB-10 / NFF-01: the lines live in the caller's transaction, all or none."""
    with pytest.raises(RuntimeError), transaction.atomic():
        finance.enregistrer([ligne()], origine='paiement')
        raise RuntimeError('coupure entre l\'encaissement et la suite')
    assert not MouvementModel.objects.exists()


def test_a_refused_line_refuses_the_whole_batch():
    with pytest.raises(finance.MouvementRefuse):
        finance.enregistrer([ligne(), ligne(nature='R01', sens=finance.SORTIE, tiers_type=None, tiers_id=None)],
                            origine='paiement')
    assert not MouvementModel.objects.exists()


# --- FB-01, FB-02: the database refuses any change and any deletion -------------------------------------------------

def test_the_database_refuses_to_update_a_line():
    pk = finance.enregistrer([ligne()], origine='paiement')[0]

    with pytest.raises(DatabaseError, match='ajout seul'):
        executer('UPDATE finance_mouvement SET montant = 1 WHERE id = %s', [pk])
    with pytest.raises(DatabaseError, match='ajout seul'), transaction.atomic():
        MouvementModel.objects.filter(pk=pk).update(montant=1)
    m = MouvementModel.objects.get(pk=pk)
    m.montant = 1
    with pytest.raises(finance.MouvementRefuse):
        m.save()
    assert MouvementModel.objects.get(pk=pk).montant == 250_000


def test_the_database_refuses_to_delete_a_line():
    pk = finance.enregistrer([ligne()], origine='paiement')[0]

    with pytest.raises(DatabaseError, match='ajout seul'):
        executer('DELETE FROM finance_mouvement WHERE id = %s', [pk])
    with pytest.raises(DatabaseError, match='ajout seul'), transaction.atomic():
        MouvementModel.objects.filter(pk=pk).delete()
    with pytest.raises(finance.MouvementRefuse):
        MouvementModel.objects.get(pk=pk).delete()
    assert MouvementModel.objects.filter(pk=pk).exists()


def test_histories_are_append_only_too():
    histo = ParametreHistoModel.objects.create(cle='commission_hote', valeur_avant=8, valeur_apres=9,
                                               date_effet=timezone.now(), motif='essai')
    corresp = CorrespondanceHistoModel.objects.create(nature_id='R01', compte_avant='7061', compte_apres='7069',
                                                      date_effet=timezone.now().date(), motif='essai')
    for table, pk in (('finance_parametre_histo', histo.pk), ('finance_correspondance_histo', corresp.pk)):
        with pytest.raises(DatabaseError, match='ajout seul'):
            executer(f'UPDATE {table} SET motif = %s WHERE id = %s', ['autre', pk])
        with pytest.raises(DatabaseError, match='ajout seul'):
            executer(f'DELETE FROM {table} WHERE id = %s', [pk])


# --- FB-03: a correction is an inverse line ---------------------------------------------------------------------

def test_a_correction_is_an_inverse_line_and_both_stay_visible():
    pk = finance.enregistrer([ligne(montant=25_000)], origine='paiement')[0]

    inverse = MouvementModel.objects.get(pk=finance.contre_passer(pk, motif='Montant saisi faux (250 000)'))

    assert (inverse.annule_mouvement_id, inverse.sens, inverse.montant, inverse.nature_id, inverse.tiers_id) == (
        pk, finance.SORTIE, 25_000, 'T01', HOTE)
    assert MouvementModel.objects.count() == 2
    assert finance.du_aux_partenaires() == []


def test_a_correction_goes_to_the_audit_log(make_user):
    """FIN-13.3: who corrected which line, with the reason."""
    admin = make_user(role='admin')
    pk = finance.enregistrer([ligne()], origine='paiement')[0]

    inverse = finance.contre_passer(pk, motif='Doublon de saisie', par_id=admin.pk)

    entree = ActivityEntryModel.objects.get(action='ecriture_corrigee')
    assert (entree.actor_id, entree.details) == (
        admin.pk, {'mouvement': pk, 'ligne_inverse': inverse, 'motif': 'Doublon de saisie'})


def test_a_correction_needs_a_reason_and_happens_once():
    pk = finance.enregistrer([ligne()], origine='paiement')[0]
    with pytest.raises(finance.MouvementRefuse, match='motif'):
        finance.contre_passer(pk, motif='  ')

    inverse = finance.contre_passer(pk, motif='Doublon')

    with pytest.raises(finance.MouvementRefuse, match='déjà été corrigée'):
        finance.contre_passer(pk, motif='Encore')
    with pytest.raises(finance.MouvementRefuse, match='elle-même une correction'):
        finance.contre_passer(inverse, motif='Annuler la correction')


def test_the_database_refuses_an_inverse_line_that_does_not_mirror_the_line():
    pk = finance.enregistrer([ligne()], origine='paiement')[0]
    commun = dict(nature_code='T01', tiers_type='hote', tiers_id=HOTE, annule_mouvement_id=pk)

    with pytest.raises(DatabaseError, match='sens opposé'):
        inserer_brut(montant=250_000, sens='entree', motif='même sens', **commun)
    with pytest.raises(DatabaseError, match='sens opposé'):
        inserer_brut(montant=1, sens='sortie', motif='autre montant', **commun)
    with pytest.raises(DatabaseError, match='motif'):
        inserer_brut(montant=250_000, sens='sortie', motif=' ', **commun)


# --- FB-04: one line per external event ---------------------------------------------------------------------------

def test_a_notification_delivered_three_times_gives_one_line():
    for _ in range(3):
        finance.enregistrer([ligne(externe_reference='TX-42')], origine='webhook')

    assert MouvementModel.objects.filter(externe_reference='TX-42').count() == 1


def test_one_payment_can_owe_the_same_nature_to_several_partners():
    """Evasion basket: one transaction, a T06 line for each provider."""
    autre = uuid.uuid4()
    lignes = [ligne(nature='T06', offre='EVASION', montant=m, tiers_type='prestataire', tiers_id=t,
                    externe_reference='TX-PANIER') for m, t in ((40_000, HOTE), (25_000, autre))]

    assert len(finance.enregistrer(lignes, origine='paiement')) == 2
    assert len(finance.enregistrer(lignes, origine='webhook')) == 0


def test_an_event_replayed_with_another_amount_is_not_written_and_alerts(admin_finance):
    finance.enregistrer([ligne(externe_reference='TX-7')], origine='webhook')
    mail.outbox.clear()

    assert finance.enregistrer([ligne(externe_reference='TX-7', montant=1_000)], origine='webhook') == []

    assert MouvementModel.objects.get(externe_reference='TX-7').montant == 250_000
    assert [m.to for m in mail.outbox] == [[admin_finance.email]]
    assert 'rejoué' in mail.outbox[0].subject and 'ligne n°' in mail.outbox[0].body


# --- FB-06 to FB-12: refused lines --------------------------------------------------------------------------------

def test_an_unknown_nature_is_refused_and_alerts_the_finance_team(admin_finance):
    """FB-06: refused by the application, and by the database for a script; the refusal is emailed through the
    notifications module to the admins who see the Finances section."""
    with pytest.raises(finance.MouvementRefuse, match='Z99'):
        finance.enregistrer([ligne(nature='Z99')], origine='paiement')

    assert [m.to for m in mail.outbox] == [[admin_finance.email]]
    assert mail.outbox[0].subject == '[Kwa-Ba Finance] Mouvement refusé par le grand livre'
    assert 'Nature « Z99 » inconnue' in mail.outbox[0].body and 'Origine : paiement' in mail.outbox[0].body
    assert "L'action qui le demandait" in mail.outbox[0].body  # plain text, no HTML escaping
    assert '250' not in mail.outbox[0].body  # never an amount in the alert (NFF-05)

    with pytest.raises(DatabaseError, match='nature Z99 inconnue'):
        inserer_brut(nature_code='Z99')


def test_the_alert_goes_to_the_admins_who_see_finances_only(make_user):
    """Super admin, admin without limits, admin granted Finances; not an admin limited to other sections, nor one
    whose access ended, nor another role."""
    voient = [make_user(role='admin', is_superuser=True, admin_sections=['avis']), make_user(role='admin'),
              make_user(role='admin', admin_sections=['documents', 'finances'])]
    make_user(role='admin', admin_sections=['avis', 'tarifs'])
    make_user(role='admin', admin_expire_le=timezone.now() - timedelta(hours=1))
    make_user(role='agent')

    with pytest.raises(finance.MouvementRefuse):
        finance.enregistrer([ligne(nature='Z99')], origine='paiement')

    assert sorted(m.to[0] for m in mail.outbox) == sorted(u.email for u in voient)


def test_a_refusal_without_anyone_to_alert_still_refuses():
    with pytest.raises(finance.MouvementRefuse):
        finance.enregistrer([ligne(nature='Z99')], origine='paiement')
    assert mail.outbox == []


def test_a_line_without_offer_is_refused():
    """FB-07"""
    with pytest.raises(finance.MouvementRefuse, match='Offre'):
        finance.enregistrer([ligne(offre=None)], origine='paiement')
    with pytest.raises(DatabaseError, match='offre .* inconnue'):
        inserer_brut(offre_code=None)


def test_a_withheld_deposit_needs_its_reason():
    """FB-08"""
    with pytest.raises(finance.MouvementRefuse, match='C03'):
        finance.enregistrer([ligne(nature='C03', sens=finance.SORTIE, montant=20_000, tiers_type=None,
                                   tiers_id=None)], origine='caution')
    with pytest.raises(DatabaseError, match='C03'):
        inserer_brut(nature_code='C03', sens='sortie', reservation_id=RESERVATION)


def test_a_direction_against_the_nature_is_refused():
    """FB-09"""
    with pytest.raises(finance.MouvementRefuse, match='attend le sens entree'):
        finance.enregistrer([ligne(nature='R01', sens=finance.SORTIE, tiers_type=None, tiers_id=None)],
                            origine='paiement')
    with pytest.raises(DatabaseError, match='attend le sens entree'):
        inserer_brut(nature_code='R01', sens='sortie')


@pytest.mark.parametrize('montant', [1999.98, Decimal('2000.50'), Decimal('2000'), '2000', True])
def test_an_amount_that_is_not_whole_francs_is_refused(montant):
    """FB-11: rounding belongs to whoever computes the split (to the franc, never against the partner), not here."""
    with pytest.raises(finance.MouvementRefuse, match='entier'):
        finance.enregistrer([ligne(montant=montant)], origine='paiement')


@pytest.mark.parametrize('montant', [0, -5_000])
def test_a_zero_or_negative_amount_is_refused(montant):
    """FB-12: the amount is positive, the direction carries the sign."""
    with pytest.raises(finance.MouvementRefuse, match='positif'):
        finance.enregistrer([ligne(montant=montant)], origine='paiement')
    with pytest.raises(DatabaseError, match='montant_positif'):
        inserer_brut(montant=montant)


@pytest.mark.parametrize('champs, message', [
    ({'nature': 'I01', 'tiers_type': None, 'tiers_id': None}, 'inactive'),      # VAT: waiting for the tax office
    ({'offre': 'EVENTS'}, "n'est pas ouverte"),                                 # offer of wave 4
    ({'compte_argent': 'BANQUE_EXP'}, 'est inactif'),                            # bank account not opened yet
    ({'compte_argent': 'PAYPAL', 'moyen_paiement': 'PAYPAL'}, 'est inactif'),    # PayPal off at launch
    ({'tiers_type': 'bailleur'}, 'est inactif'),
])
def test_inactive_codes_are_refused(champs, message):
    with pytest.raises(finance.MouvementRefuse, match=message):
        finance.enregistrer([ligne(**champs)], origine='paiement')


def test_the_database_refuses_an_offer_or_account_not_open():
    with pytest.raises(DatabaseError, match='offre EVENTS non ouverte'):
        inserer_brut(offre_code='EVENTS')
    with pytest.raises(DatabaseError, match='BANQUE_EXP inactif'):
        inserer_brut(compte_argent_code='BANQUE_EXP')


def test_partner_money_names_the_partner_and_a_deposit_names_its_object():
    with pytest.raises(finance.MouvementRefuse, match='tiers'):
        finance.enregistrer([ligne(tiers_type=None, tiers_id=None)], origine='paiement')
    with pytest.raises(finance.MouvementRefuse, match='réservation ou la location'):
        finance.enregistrer([ligne(nature='C01', montant=100_000, tiers_type=None, tiers_id=None,
                                   reservation_id=None)], origine='paiement')


# --- FI-02: no writing in a locked month --------------------------------------------------------------------------

def test_a_locked_month_refuses_any_line():
    finance.enregistrer([ligne()], origine='paiement')
    PeriodeModel.objects.filter(mois=finance.mois_de(timezone.now())).update(
        etat=PeriodeModel.VERROUILLEE, verrouillee_le=timezone.now())

    with pytest.raises(finance.MouvementRefuse, match='verrouillée'):
        finance.enregistrer([ligne(nature='R01', montant=15_000, tiers_type=None, tiers_id=None)], origine='paiement')
    with pytest.raises(DatabaseError, match='verrouillée'):
        inserer_brut()


def test_the_accounting_month_is_the_month_of_the_event():
    moment = timezone.now()
    autre_mois = finance.mois_de(moment - timedelta(days=40))
    PeriodeModel.objects.get_or_create(mois=autre_mois)

    with pytest.raises(DatabaseError, match='incohérent'):
        inserer_brut(date_evenement=moment, mois_comptable=autre_mois)
    # An inventory entry (origine « calcul ») may be booked in another month
    inserer_brut(date_evenement=moment, mois_comptable=autre_mois, origine='calcul', nature_code='D20',
                 sens='sortie', offre_code='STRUCTURE')
