import datetime
import uuid
from typing import Optional

from apps.messaging.domain.entities.MessageReport import MessageReport
from apps.messaging.domain.entities.Sanction import Sanction
from apps.messaging.domain.exceptions import (
    ContestNotAllowedException,
    InvalidReportException,
    InvalidReportStateException,
    ReportNotFoundException,
    SameReviewerException,
    SanctionNotFoundException,
)
from apps.messaging.infrastructure.container import moderation_service

__all__ = ['ModerationNotFound', 'ModerationRefused', 'report_detail', 'confirm_report', 'reject_report',
           'set_legal_hold', 'sanction_detail', 'review_contest', 'lift_sanction']


class ModerationNotFound(Exception):
    pass


class ModerationRefused(Exception):
    pass


def _report_json(report: MessageReport) -> dict:
    return {
        'id': report.id,
        'conversation_id': str(report.conversation_id),
        'message_id': report.message_id,
        'reporter_id': str(report.reporter_id),
        'author_id': str(report.author_id),
        'reason': report.reason,
        'details': report.details,
        'status': report.status,
        'created_at': report.created_at,
        'message_created_at': report.message_created_at,
        'reviewed_at': report.reviewed_at,
        'review_note': report.review_note,
        'legal_hold': report.legal_hold,
        'context': [{'message_id': c.message_id, 'from_author': c.from_author, 'content': c.content,
                     'created_at': c.created_at, 'reported': c.reported} for c in report.context],
    }


def _sanction_json(sanction: Sanction) -> dict:
    return {
        'id': sanction.id,
        'user_id': str(sanction.user_id),
        'report_id': sanction.report_id,
        'step': sanction.step,
        'category': sanction.category,
        'created_at': sanction.created_at,
        'starts_at': sanction.starts_at,
        'ends_at': sanction.ends_at,
        'cancelled_at': sanction.cancelled_at,
        'contested_at': sanction.contested_at,
        'contest_text': sanction.contest_text,
        'contest_status': sanction.contest_status,
        'contest_note': sanction.contest_note,
    }


def _call(action):
    try:
        return action()
    except (ReportNotFoundException, SanctionNotFoundException) as e:
        raise ModerationNotFound(str(e)) from e
    except (InvalidReportStateException, ContestNotAllowedException, SameReviewerException,
            InvalidReportException) as e:
        raise ModerationRefused(str(e)) from e


def report_detail(report_id: int) -> dict:
    return _call(lambda: _report_json(moderation_service().get_report(report_id)))


def confirm_report(admin_id: uuid.UUID, report_id: int, note: str = '') -> dict:
    return _call(lambda: _sanction_json(moderation_service().confirm_report(admin_id, report_id, note)))


def reject_report(admin_id: uuid.UUID, report_id: int, note: str = '') -> dict:
    return _call(lambda: _report_json(moderation_service().reject_report(admin_id, report_id, note)))


def set_legal_hold(report_id: int, hold: bool) -> dict:
    return _call(lambda: _report_json(moderation_service().set_legal_hold(report_id, hold)))


def sanction_detail(sanction_id: int) -> dict:
    return _call(lambda: _sanction_json(moderation_service().get_sanction(sanction_id)))


def review_contest(admin_id: uuid.UUID, sanction_id: int, accept: bool, note: str = '') -> dict:
    return _call(lambda: _sanction_json(moderation_service().review_contest(admin_id, sanction_id, accept, note)))


def lift_sanction(sanction_id: int, ends_at: Optional[datetime.datetime] = None) -> dict:
    return _call(lambda: _sanction_json(moderation_service().lift(sanction_id, ends_at)))
