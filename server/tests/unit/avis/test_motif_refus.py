import datetime
import uuid
from types import SimpleNamespace

import pytest

from apps.avis import services
from apps.avis.services import DELAI_AVIS_JOURS, motif_refus

TODAY = datetime.date(2026, 10, 8)
GUEST = SimpleNamespace(id=uuid.uuid4())


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    monkeypatch.setattr(services.timezone, 'localdate', lambda: TODAY)


def _stay(check_out=TODAY - datetime.timedelta(days=1), status='confirmed', guest=GUEST):
    return {'voyageur_id': guest.id, 'statut': status, 'check_out': check_out}


def test_finished_confirmed_stay_can_be_reviewed():
    assert motif_refus(_stay(), GUEST.id, False) is None


def test_other_guest_rejected():
    assert motif_refus(_stay(), uuid.uuid4(), False) is not None


@pytest.mark.parametrize('status', ['pending', 'cancelled'])
def test_unconfirmed_stay_rejected(status):
    assert motif_refus(_stay(status=status), GUEST.id, False) is not None


def test_future_check_out_rejected():
    assert motif_refus(_stay(check_out=TODAY + datetime.timedelta(days=1)), GUEST.id, False) is not None


@pytest.mark.parametrize('days_ago, allowed', [(0, True), (DELAI_AVIS_JOURS, True), (DELAI_AVIS_JOURS + 1, False)])
def test_review_window_boundaries(days_ago, allowed):
    stay = _stay(check_out=TODAY - datetime.timedelta(days=days_ago))
    assert (motif_refus(stay, GUEST.id, False) is None) is allowed


def test_already_reviewed_rejected():
    assert motif_refus(_stay(), GUEST.id, True) is not None
