import importlib
from types import SimpleNamespace

from apps.activity.domain import catalogue
from apps.activity.domain.entities import Target

backfill = importlib.import_module('apps.activity.migrations.0003_backfill_actor_and_target')


def test_every_action_has_a_known_category_and_level():
    for code, item in catalogue.ACTIONS.items():
        assert item.label, code
        assert item.category in catalogue.CATEGORIES, code
        assert item.level in catalogue.LEVELS, code


def test_target_found_in_the_details():
    assert catalogue.resolve_target('annonce_supprimee', {'annonce_id': 'l1', 'annonce': 'Villa'}) == \
        Target('listing', 'l1', 'Villa')
    assert catalogue.resolve_target('role_modifie', {'cible_id': 'u1', 'cible_email': 'a@b.tg'}) == \
        Target('account', 'u1', 'a@b.tg')
    assert catalogue.resolve_target('visit_moved', {'appointment': 'v1', 'title': 'Studio'}) == \
        Target('appointment', 'v1', 'Studio')
    assert catalogue.resolve_target('backoffice_modification', {'objet': 'ong', 'id': '4', 'libelle': 'Aide'}) == \
        Target('object', '4', 'Aide')
    assert catalogue.resolve_target('connexion', {}) is None
    assert catalogue.resolve_target('unknown_action', {'annonce_id': 'l1'}) is None


def test_readable_summaries():
    assert catalogue.summary('role_modifie', {'avant': 'voyageur', 'apres': 'hote'}, Target('account', 'u', 'Jean')) \
        == 'Jean · voyageur → hote'
    assert catalogue.summary('connexion_bloquee', {'email': 'a@b.tg'}, None) == 'a@b.tg · trop de tentatives'
    assert catalogue.summary('finances_exportees', {'format': 'csv', 'debut': '2026-10-01', 'fin': '2026-10-31'},
                             None) == 'CSV · 2026-10-01 → 2026-10-31'
    assert catalogue.summary('agenda_settings_changed', {'changes': {'a': {}, 'b': {}}}, None) == \
        '2 réglages modifiés'
    assert catalogue.summary('backoffice_suppression', {'objet': 'experience', 'libelle': 'Kayak'},
                             Target('object', '1', 'Kayak')) == 'Expérience · Kayak'
    assert catalogue.summary('visit_post_check', {'compliant': False}, Target('appointment', '1', 'Villa')) == \
        'Villa · non conforme'


def test_detail_lines_in_french_with_before_and_after():
    lines = catalogue.detail_lines('tarifs_modifies', {'avant': {'frais_voyageur': 0.06, 'frais_reduits': 0.03},
                                                       'apres': {'frais_voyageur': 0.07, 'frais_reduits': 0.03}})
    assert lines == [{'label': 'Frais voyageur', 'value': '0.06 → 0.07'}]
    lines = catalogue.detail_lines('agenda_settings_changed',
                                   {'changes': {'notice_hours': {'before': 24, 'after': 48}}})
    assert lines == [{'label': 'Préavis (h)', 'value': '24 → 48'}]
    lines = catalogue.detail_lines('validated_without_visit', {'motif': 'Hôtel connu', 'keep_visit': True})
    assert lines == [{'label': 'Motif', 'value': 'Hôtel connu'}, {'label': 'Visite conservée', 'value': 'oui'}]


def test_levels_split_the_actions():
    routine = catalogue.actions_of(levels={catalogue.ROUTINE})
    assert 'connexion' in routine and 'role_modifie' not in routine
    assert 'role_modifie' in catalogue.actions_of(levels={catalogue.SENSITIVE})
    assert set(catalogue.actions_of(categories={catalogue.AGENDA})) >= {'visit_moved', 'visit_booked'}


def _row(action, actor_id='u1', actor_email='u@x.tg', **details):
    return SimpleNamespace(action=action, actor_id=actor_id, actor_email=actor_email, details=details)


def test_history_backfill_puts_the_author_and_the_target_back_in_place():
    actor, email, target = backfill._resolve(_row('role_modifie', avant='voyageur', apres='hote', agent_id='a1',
                                                  annonce_id='l1'))
    assert (actor, email, target) == ('a1', '', Target('account', 'u1', 'u@x.tg'))
    actor, email, target = backfill._resolve(_row('role_modifie', cible_id='u2', cible_email='c@x.tg'))
    assert (actor, target) == ('u1', Target('account', 'u2', 'c@x.tg'))
    actor, email, target = backfill._resolve(_row('super_admin_nomme'))
    assert (actor, target) == (None, Target('account', 'u1', 'u@x.tg'))
    actor, email, target = backfill._resolve(_row('mission_prise', type='piece', cible='h1'))
    assert target == Target('account', 'h1', '')
    actor, email, target = backfill._resolve(_row('annonce_verifiee', hebergement='l9'))
    assert (actor, target) == ('u1', Target('listing', 'l9', ''))
