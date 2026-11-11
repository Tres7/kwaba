import datetime
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from apps.messaging.domain.exceptions import InvalidReportException

REASONS = ('insult', 'hate', 'threat', 'harassment', 'spam', 'scam', 'other')
PENDING, CONFIRMED, REJECTED = 'pending', 'confirmed', 'rejected'


@dataclass
class ContextMessage:
    message_id: int
    from_author: bool
    content: str
    created_at: datetime.datetime
    reported: bool = False


@dataclass
class MessageReport:
    DETAILS_MAX_LENGTH = 500

    conversation_id: uuid.UUID
    message_id: int
    reporter_id: uuid.UUID
    author_id: uuid.UUID
    reason: str
    message_created_at: datetime.datetime
    details: str = ''
    context: List[ContextMessage] = field(default_factory=list)
    id: Optional[int] = None
    status: str = PENDING
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    reviewed_at: Optional[datetime.datetime] = None
    reviewed_by_id: Optional[uuid.UUID] = None
    review_note: str = ''
    legal_hold: bool = False

    @staticmethod
    def validate(reason: str, details: str) -> tuple[str, str]:
        reason = (reason or '').strip()
        details = (details or '').strip()
        if reason not in REASONS:
            raise InvalidReportException("Motif de signalement invalide.")
        if len(details) > MessageReport.DETAILS_MAX_LENGTH:
            raise InvalidReportException(
                f"Le détail ne peut pas dépasser {MessageReport.DETAILS_MAX_LENGTH} caractères.")
        return reason, details

    @property
    def pending(self) -> bool:
        return self.status == PENDING

    def review(self, status: str, admin_id: uuid.UUID, note: str, now: datetime.datetime) -> None:
        self.status, self.reviewed_by_id, self.reviewed_at, self.review_note = status, admin_id, now, note
