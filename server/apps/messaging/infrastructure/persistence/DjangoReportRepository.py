import datetime
import uuid
from typing import List, Optional

from apps.messaging.domain.entities.MessageReport import CONFIRMED, REJECTED, ContextMessage, MessageReport
from apps.messaging.domain.repositories.ReportRepository import ReportRepository
from apps.messaging.infrastructure.persistence.models import MessageReportModel

FIELDS = ('conversation_id', 'message_id', 'reporter_id', 'author_id', 'reason', 'details', 'message_created_at',
          'created_at', 'status', 'reviewed_at', 'reviewed_by_id', 'review_note', 'legal_hold')


def _context_to_json(context: List[ContextMessage]) -> list:
    return [{'message_id': c.message_id, 'from_author': c.from_author, 'content': c.content,
             'created_at': c.created_at.isoformat(), 'reported': c.reported} for c in context]


def _context_from_json(rows: list) -> List[ContextMessage]:
    return [ContextMessage(r['message_id'], r['from_author'], r['content'],
                           datetime.datetime.fromisoformat(r['created_at']), r.get('reported', False)) for r in rows]


class DjangoReportRepository(ReportRepository):

    def _to_entity(self, model: MessageReportModel) -> MessageReport:
        return MessageReport(id=model.id, context=_context_from_json(model.context),
                             **{f: getattr(model, f) for f in FIELDS})

    def add(self, report: MessageReport) -> MessageReport:
        model = MessageReportModel.objects.create(context=_context_to_json(report.context),
                                                  **{f: getattr(report, f) for f in FIELDS})
        return self._to_entity(model)

    def get(self, report_id: int) -> Optional[MessageReport]:
        model = MessageReportModel.objects.filter(pk=report_id).first()
        return self._to_entity(model) if model else None

    def find(self, reporter_id: uuid.UUID, message_id: int) -> Optional[MessageReport]:
        model = MessageReportModel.objects.filter(reporter_id=reporter_id, message_id=message_id).first()
        return self._to_entity(model) if model else None

    def save(self, report: MessageReport) -> None:
        MessageReportModel.objects.filter(pk=report.id).update(**{f: getattr(report, f) for f in FIELDS})

    def confirmed_case_dates(self, author_id: uuid.UUID) -> List[datetime.datetime]:
        return list(MessageReportModel.objects.filter(author_id=author_id, status=CONFIRMED)
                    .values_list('message_created_at', flat=True))

    def rejected_count_since(self, reporter_id: uuid.UUID, since: datetime.datetime) -> int:
        return MessageReportModel.objects.filter(reporter_id=reporter_id, status=REJECTED,
                                                 reviewed_at__gte=since).count()
