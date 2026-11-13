from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.messaging import api as messaging
from apps.securite import fraude
from apps.activity import api as activity
from apps.securite.backoffice import nom
from apps.securite.permissions import EstAdministrateur
from apps.users import api as users


def _person(user_id: str) -> dict:
    account = users.compte(user_id)
    return {'id': user_id, 'nom': nom(account) if account else '', 'email': account.email if account else ''}


def _run(action):
    try:
        return Response(action())
    except messaging.ModerationNotFound as e:
        return Response({'detail': str(e) or 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
    except messaging.ModerationRefused as e:
        return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)


def _note(request) -> str:
    return str(request.data.get('note', ''))[:1000]


class ReportDetailView(APIView):
    permission_classes = [EstAdministrateur]

    def get(self, request, pk):
        def detail():
            report = messaging.report_detail(pk)
            activity.record('report_viewed', request, actor=request.user, report=pk)
            return {**report, 'reporter': _person(report['reporter_id']), 'author': _person(report['author_id'])}
        return _run(detail)


class ReportConfirmView(APIView):
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        def confirm():
            sanction = messaging.confirm_report(request.user.pk, pk, _note(request))
            activity.record('report_confirmed', request, actor=request.user, report=pk, step=sanction['step'])
            return sanction
        return _run(confirm)


class ReportRejectView(APIView):
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        def reject():
            report = messaging.reject_report(request.user.pk, pk, _note(request))
            activity.record('report_rejected', request, actor=request.user, report=pk)
            return {'id': report['id'], 'status': report['status']}
        return _run(reject)


class ReportLegalHoldView(APIView):
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        hold = request.data.get('hold') is True

        def change():
            report = messaging.set_legal_hold(pk, hold)
            fraude.set_legal_hold('report', pk, hold)
            activity.record('legal_hold_changed', request, actor=request.user, report=pk, hold=hold)
            activity.hold('report', pk, hold)
            return {'id': report['id'], 'legal_hold': report['legal_hold']}
        return _run(change)


class SanctionDetailView(APIView):
    permission_classes = [EstAdministrateur]

    def get(self, request, pk):
        def detail():
            sanction = messaging.sanction_detail(pk)
            return {**sanction, 'user': _person(sanction['user_id'])}
        return _run(detail)


class ContestReviewView(APIView):
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        accept = request.data.get('accept') is True

        def review():
            sanction = messaging.review_contest(request.user.pk, pk, accept, _note(request))
            activity.record('contest_reviewed', request, actor=request.user, sanction=pk, accepted=accept)
            return sanction
        return _run(review)


class SanctionLiftView(APIView):
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        raw = request.data.get('ends_at')
        ends_at = parse_datetime(str(raw)) if raw else None
        if raw and ends_at is None:
            return Response({'ends_at': ['Date invalide.']}, status=status.HTTP_400_BAD_REQUEST)

        def lift():
            sanction = messaging.lift_sanction(pk, ends_at)
            activity.record('sanction_lifted', request, actor=request.user, sanction=pk,
                            ends_at=sanction['ends_at'].isoformat())
            return sanction
        return _run(lift)
