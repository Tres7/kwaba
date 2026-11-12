from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.messaging.domain.entities.Sanction import Sanction
from apps.messaging.domain.exceptions import (
    CannotReportOwnMessageException,
    ContestNotAllowedException,
    ConversationNotFoundException,
    InvalidReportException,
    MessageNotFoundException,
    SanctionNotFoundException,
)
from apps.messaging.infrastructure.container import moderation_service
from apps.messaging.infrastructure.http.controllers.ConversationController import WriteGuardsMixin


def _detail(e: Exception, code: int) -> Response:
    return Response({'detail': str(e)}, status=code)


def sanction_json(sanction: Sanction, contestable: bool) -> dict:
    return {
        'id': sanction.id,
        'step': sanction.step,
        'category': sanction.category,
        'created_at': sanction.created_at,
        'ends_at': sanction.ends_at,
        'cancelled': sanction.cancelled,
        'contest_status': sanction.contest_status,
        'contestable': contestable,
    }


class DraftCheckView(WriteGuardsMixin, APIView):
    throttle_scope = 'messaging_moderation_check'

    def post(self, request):
        verdict = moderation_service().check_draft(str(request.data.get('content', ''))[:2000])
        return Response({'level': verdict.level, 'categories': list(verdict.categories)})


class FalsePositiveView(WriteGuardsMixin, APIView):
    throttle_scope = 'messaging_report'

    def post(self, request, conversation_id):
        try:
            recorded = moderation_service().report_false_positive(
                request.user.id, conversation_id, str(request.data.get('content', '')))
        except ConversationNotFoundException as e:
            return _detail(e, status.HTTP_404_NOT_FOUND)
        return Response({'recorded': recorded}, status=status.HTTP_201_CREATED)


class MessageReportView(WriteGuardsMixin, APIView):
    throttle_scope = 'messaging_report'

    def post(self, request, conversation_id, message_id):
        try:
            report, created = moderation_service().report_message(
                request.user.id, conversation_id, message_id,
                str(request.data.get('reason', '')), str(request.data.get('details', '')),
            )
        except (ConversationNotFoundException, MessageNotFoundException) as e:
            return _detail(e, status.HTTP_404_NOT_FOUND)
        except CannotReportOwnMessageException as e:
            return _detail(e, status.HTTP_403_FORBIDDEN)
        except InvalidReportException as e:
            return _detail(e, status.HTTP_400_BAD_REQUEST)
        return Response({'id': report.id, 'reason': report.reason},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ModerationStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = moderation_service()
        current = service.status(request.user.id)
        return Response({
            'suspended_until': current.suspended_until,
            'sanctions': [sanction_json(s, service.is_contestable(s)) for s in current.sanctions],
        })


class SanctionContestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, sanction_id):
        service = moderation_service()
        try:
            sanction = service.contest(request.user.id, sanction_id, str(request.data.get('text', '')))
        except SanctionNotFoundException as e:
            return _detail(e, status.HTTP_404_NOT_FOUND)
        except ContestNotAllowedException as e:
            return _detail(e, status.HTTP_409_CONFLICT)
        except InvalidReportException as e:
            return _detail(e, status.HTTP_400_BAD_REQUEST)
        return Response(sanction_json(sanction, service.is_contestable(sanction)))
