import datetime
import uuid
from dataclasses import dataclass
from typing import List, Optional

from apps.messaging.application.ports.ModerationGuard import ENFORCE, ModerationGuard, ModerationVerdict
from apps.messaging.application.ports.ModerationQueue import ModerationQueue
from apps.messaging.application.ports.SanctionNotifier import SanctionNotifier
from apps.messaging.application.ports.TransactionManager import TransactionManager
from apps.messaging.domain.entities.Message import Message
from apps.messaging.domain.entities.MessageReport import CONFIRMED, REJECTED, ContextMessage, MessageReport
from apps.messaging.domain.entities.Sanction import CONTEST_ACCEPTED, CONTEST_PENDING, CONTEST_REJECTED, Sanction
from apps.messaging.domain.exceptions import (
    CannotReportOwnMessageException,
    ContestNotAllowedException,
    ConversationNotFoundException,
    InvalidReportException,
    InvalidReportStateException,
    MessageNotFoundException,
    MessagingSuspendedException,
    ReportNotFoundException,
    SameReviewerException,
    SanctionNotFoundException,
)
from apps.messaging.domain.repositories.ConversationRepository import ConversationRepository
from apps.messaging.domain.repositories.MessageRepository import MessageRepository
from apps.messaging.domain.repositories.ReportRepository import ReportRepository
from apps.messaging.domain.repositories.SanctionRepository import SanctionRepository
from apps.messaging.domain.services import SanctionLadder
from apps.messaging.domain.services.SanctionLadder import LadderPolicy


@dataclass(frozen=True)
class ModerationSettings:
    policy: LadderPolicy = LadderPolicy()
    contest_delay: datetime.timedelta = datetime.timedelta(days=14)
    context_messages: int = 10
    context_period: datetime.timedelta = datetime.timedelta(days=7)
    abusive_reporter_threshold: int = 3


@dataclass(frozen=True)
class ModerationStatus:
    suspended_until: Optional[datetime.datetime]
    sanctions: List[Sanction]


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class ModerationService:
    CONTEST_MIN_LENGTH = 5
    CONTEST_MAX_LENGTH = 1000
    NOTE_MAX_LENGTH = 1000
    STATUS_SANCTIONS = 20

    def __init__(
        self,
        conversations: ConversationRepository,
        messages: MessageRepository,
        reports: ReportRepository,
        sanctions: SanctionRepository,
        guard: ModerationGuard,
        queue: ModerationQueue,
        notifier: SanctionNotifier,
        tx: TransactionManager,
        settings: ModerationSettings = ModerationSettings(),
        clock=_now,
    ):
        self._conversations = conversations
        self._messages = messages
        self._reports = reports
        self._sanctions = sanctions
        self._guard = guard
        self._queue = queue
        self._notifier = notifier
        self._tx = tx
        self._settings = settings
        self._clock = clock

    def _conversation_of(self, user_id: uuid.UUID, conversation_id: uuid.UUID):
        conversation = self._conversations.find_by_id(conversation_id)
        if conversation is None or not conversation.is_participant(user_id):
            raise ConversationNotFoundException(str(conversation_id))
        return conversation

    def ensure_can_write(self, user_id: uuid.UUID) -> None:
        until = self._sanctions.active_suspension_end(user_id, self._clock())
        if until:
            raise MessagingSuspendedException(until)

    def check_draft(self, content: str) -> ModerationVerdict:
        if self._guard.mode() != ENFORCE:
            return ModerationVerdict()
        return self._guard.screen(content or '')

    def report_false_positive(self, user_id: uuid.UUID, conversation_id: uuid.UUID, content: str) -> bool:
        self._conversation_of(user_id, conversation_id)
        content = (content or '').strip()[:Message.MAX_LENGTH]
        verdict = self._guard.screen(content)
        if verdict.flagged:
            self._guard.record_false_positive(user_id, conversation_id, verdict, content)
        return verdict.flagged

    def report_message(self, reporter_id: uuid.UUID, conversation_id: uuid.UUID, message_id: int,
                       reason: str, details: str = '') -> tuple[MessageReport, bool]:
        reason, details = MessageReport.validate(reason, details)
        self._conversation_of(reporter_id, conversation_id)
        message = self._messages.get(message_id)
        if message is None or message.conversation_id != conversation_id:
            raise MessageNotFoundException(str(message_id))
        if message.sender_id == reporter_id:
            raise CannotReportOwnMessageException("Vous ne pouvez pas signaler votre propre message.")
        existing = self._reports.find(reporter_id, message_id)
        if existing:
            return existing, False

        since = message.created_at - self._settings.context_period
        previous = self._messages.context_before(conversation_id, message_id, since, self._settings.context_messages)
        context = [ContextMessage(m.id, m.sender_id == message.sender_id, m.content, m.created_at) for m in previous]
        context.append(ContextMessage(message.id, True, message.content, message.created_at, reported=True))

        with self._tx.atomic():
            report = self._reports.add(MessageReport(
                conversation_id=conversation_id, message_id=message_id, reporter_id=reporter_id,
                author_id=message.sender_id, reason=reason, details=details,
                message_created_at=message.created_at, context=context,
            ))
            self._queue.report_received(report, message.preview())
        return report, True

    def get_report(self, report_id: int) -> MessageReport:
        report = self._reports.get(report_id)
        if report is None:
            raise ReportNotFoundException(str(report_id))
        return report

    def _pending_report(self, report_id: int) -> MessageReport:
        report = self.get_report(report_id)
        if not report.pending:
            raise InvalidReportStateException("Ce signalement a déjà été traité.")
        return report

    def confirm_report(self, admin_id: uuid.UUID, report_id: int, note: str = '') -> Sanction:
        with self._tx.atomic():
            report = self._pending_report(report_id)
            now = self._clock()
            report.review(CONFIRMED, admin_id, (note or '')[:self.NOTE_MAX_LENGTH], now)
            self._reports.save(report)
            outcome = SanctionLadder.evaluate(
                self._reports.confirmed_case_dates(report.author_id),
                self._sanctions.applied_suspensions(report.author_id),
                self._sanctions.admin_decision_count(report.author_id),
                self._settings.policy, now,
            )
            sanction = self._sanctions.add(Sanction(
                user_id=report.author_id, report_id=report.id, step=outcome.step, category=report.reason,
                created_at=now, starts_at=outcome.starts_at, ends_at=outcome.ends_at,
            ))
            self._queue.report_closed(report)
            self._queue.sanction_applied(sanction)
            self._notifier.sanction_applied(sanction)
        return sanction

    def _reject(self, report: MessageReport, admin_id: uuid.UUID, note: str) -> None:
        now = self._clock()
        report.review(REJECTED, admin_id, (note or '')[:self.NOTE_MAX_LENGTH], now)
        self._reports.save(report)
        self._queue.report_closed(report)
        rejected = self._reports.rejected_count_since(report.reporter_id, now - self._settings.policy.window)
        if rejected == self._settings.abusive_reporter_threshold:
            self._queue.abusive_reporter(report.reporter_id, rejected)

    def reject_report(self, admin_id: uuid.UUID, report_id: int, note: str = '') -> MessageReport:
        with self._tx.atomic():
            report = self._pending_report(report_id)
            self._reject(report, admin_id, note)
        return report

    def set_legal_hold(self, report_id: int, hold: bool) -> MessageReport:
        report = self.get_report(report_id)
        report.legal_hold = bool(hold)
        self._reports.save(report)
        return report

    def get_sanction(self, sanction_id: int) -> Sanction:
        sanction = self._sanctions.get(sanction_id)
        if sanction is None:
            raise SanctionNotFoundException(str(sanction_id))
        return sanction

    def status(self, user_id: uuid.UUID) -> ModerationStatus:
        return ModerationStatus(
            suspended_until=self._sanctions.active_suspension_end(user_id, self._clock()),
            sanctions=self._sanctions.for_user(user_id, self.STATUS_SANCTIONS),
        )

    def is_contestable(self, sanction: Sanction) -> bool:
        return sanction.contestable_at(self._clock(), self._settings.contest_delay)

    def contest(self, user_id: uuid.UUID, sanction_id: int, text: str) -> Sanction:
        text = (text or '').strip()
        if not self.CONTEST_MIN_LENGTH <= len(text) <= self.CONTEST_MAX_LENGTH:
            raise InvalidReportException(
                f"Expliquez votre contestation en {self.CONTEST_MIN_LENGTH} à {self.CONTEST_MAX_LENGTH} caractères.")
        with self._tx.atomic():
            sanction = self.get_sanction(sanction_id)
            if sanction.user_id != user_id:
                raise SanctionNotFoundException(str(sanction_id))
            if not self.is_contestable(sanction):
                raise ContestNotAllowedException("Cette sanction ne peut plus être contestée.")
            sanction.contested_at, sanction.contest_text, sanction.contest_status = self._clock(), text, CONTEST_PENDING
            self._sanctions.save(sanction)
            self._queue.contest_received(sanction)
        return sanction

    def review_contest(self, admin_id: uuid.UUID, sanction_id: int, accept: bool, note: str = '') -> Sanction:
        with self._tx.atomic():
            sanction = self.get_sanction(sanction_id)
            if sanction.contest_status != CONTEST_PENDING:
                raise ContestNotAllowedException("Aucune contestation en attente pour cette sanction.")
            report = self.get_report(sanction.report_id)
            other_admins = [a for a in self._queue.active_admin_ids() if a != admin_id]
            if report.reviewed_by_id == admin_id and other_admins:
                raise SameReviewerException(
                    "La contestation doit être examinée par un autre administrateur que celui qui a confirmé le signalement.")
            now = self._clock()
            sanction.contest_status = CONTEST_ACCEPTED if accept else CONTEST_REJECTED
            sanction.contest_reviewed_at, sanction.contest_reviewed_by_id = now, admin_id
            sanction.contest_note = (note or '')[:self.NOTE_MAX_LENGTH]
            if accept:
                for linked in self._sanctions.for_report(report.id):
                    linked.cancel(now)
                    if linked.id != sanction.id:
                        self._sanctions.save(linked)
                sanction.cancel(now)
                self._reject(report, admin_id, sanction.contest_note)
            self._sanctions.save(sanction)
            self._queue.contest_closed(sanction)
            self._notifier.contest_reviewed(sanction)
        return sanction

    def lift(self, sanction_id: int, ends_at: Optional[datetime.datetime] = None) -> Sanction:
        with self._tx.atomic():
            sanction = self.get_sanction(sanction_id)
            now = self._clock()
            if not sanction.active_at(now):
                raise ContestNotAllowedException("Cette sanction n'est pas une suspension en cours.")
            target = now if ends_at is None else ends_at
            if not now <= target < sanction.ends_at:
                raise InvalidReportException("La nouvelle fin doit être entre maintenant et la fin actuelle.")
            sanction.ends_at = target
            self._sanctions.save(sanction)
        return sanction
