import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.hebergements import views as hebergement_views
from apps.hebergements.models import BlocageModel
from apps.reservations import serializers as reservation_serializers
from apps.reservations.models import ReservationModel

pytestmark = pytest.mark.django_db(transaction=True)


def _interleave(monkeypatch, *targets):
    """Makes each request wait, after its availability check, until the other one has checked too.

    Without a lock, both see the dates free then both write. With the listing lock,
    the second one stays blocked before its check: the wait times out and the first one finishes alone.
    """
    barrier = threading.Barrier(2, timeout=3)
    for module, name in targets:
        original = getattr(module, name)

        def check_then_wait(*args, _original=original, **kwargs):
            result = _original(*args, **kwargs)
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                pass
            return result

        monkeypatch.setattr(module, name, check_then_wait)


def _run_concurrently(*requests):
    statuses = []

    def run(user, method, url, payload):
        client = APIClient()
        client.raise_request_exception = False
        client.force_authenticate(user=user)
        try:
            statuses.append(getattr(client, method)(url, payload, format='json').status_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=request) for request in requests]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)
    return statuses


def _stay(days=3):
    check_in = timezone.localdate() + timedelta(days=10)
    return check_in, check_in + timedelta(days=days)


def test_two_simultaneous_bookings_of_same_dates_only_one_succeeds(make_user, make_hebergement, monkeypatch):
    hebergement = make_hebergement()
    check_in, check_out = _stay()
    payload = {'hebergement': str(hebergement.id), 'check_in': check_in.isoformat(), 'check_out': check_out.isoformat()}
    _interleave(monkeypatch, (reservation_serializers, 'conflit'))

    statuses = _run_concurrently(
        (make_user(), 'post', '/api/v1/reservations/', payload),
        (make_user(), 'post', '/api/v1/reservations/', payload),
    )

    assert sorted(statuses) == [201, 400]
    assert ReservationModel.objects.filter(hebergement=hebergement).count() == 1


def test_host_closing_dates_while_guest_books_them_only_one_succeeds(make_user, make_hebergement, monkeypatch):
    hebergement = make_hebergement()
    check_in, check_out = _stay()
    _interleave(monkeypatch, (reservation_serializers, 'conflit'), (hebergement_views, 'a_des_reservations'))

    statuses = _run_concurrently(
        (make_user(), 'post', '/api/v1/reservations/',
         {'hebergement': str(hebergement.id), 'check_in': check_in.isoformat(), 'check_out': check_out.isoformat()}),
        (hebergement.host, 'post', f'/api/v1/hebergements/{hebergement.id}/blocages/',
         {'debut': check_in.isoformat(), 'fin': check_out.isoformat()}),
    )

    # Depending on the arrival order: booking accepted and closure refused (409), or the reverse (400)
    assert sorted(statuses) in ([201, 400], [201, 409])
    reservations = ReservationModel.objects.filter(hebergement=hebergement).count()
    blocages = BlocageModel.objects.filter(hebergement=hebergement).count()
    assert reservations + blocages == 1
