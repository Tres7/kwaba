import uuid

from apps.messaging.application.ports.ModerationQueue import ModerationQueue
from apps.messaging.domain.entities.MessageReport import MessageReport
from apps.messaging.domain.entities.Sanction import Sanction
from apps.messaging.domain.services.SanctionLadder import ADMIN_DECISION
from apps.securite import fraude
from apps.users import api as users


class DjangoModerationQueue(ModerationQueue):

    def report_received(self, report: MessageReport, excerpt: str) -> None:
        fraude.record_report(report.author_id, report.id, report.reason, excerpt)

    def report_closed(self, report: MessageReport) -> None:
        fraude.close('report', report.id, report.reviewed_by_id, report.review_note)

    def sanction_applied(self, sanction: Sanction) -> None:
        fraude.record_sanction(sanction.user_id, sanction.id, sanction.step, sanction.step == ADMIN_DECISION)

    def contest_received(self, sanction: Sanction) -> None:
        fraude.record_contest(sanction.user_id, sanction.id, sanction.contest_text)

    def contest_closed(self, sanction: Sanction) -> None:
        fraude.close('contest', sanction.id, sanction.contest_reviewed_by_id, sanction.contest_note)

    def abusive_reporter(self, reporter_id: uuid.UUID, rejected_count: int) -> None:
        fraude.record_abusive_reporter(reporter_id, rejected_count)

    def active_admin_ids(self) -> list[uuid.UUID]:
        return users.ids_actifs(['admin'])
