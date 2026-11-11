import datetime
import uuid
from dataclasses import dataclass, field
from typing import Optional

from apps.messaging.domain.services.SanctionLadder import SUSPENSIONS

CONTEST_PENDING, CONTEST_ACCEPTED, CONTEST_REJECTED = 'pending', 'accepted', 'rejected'


@dataclass
class Sanction:
    user_id: uuid.UUID
    report_id: int
    step: str
    category: str
    id: Optional[int] = None
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    starts_at: Optional[datetime.datetime] = None
    ends_at: Optional[datetime.datetime] = None
    cancelled_at: Optional[datetime.datetime] = None
    contested_at: Optional[datetime.datetime] = None
    contest_text: str = ''
    contest_status: str = ''
    contest_reviewed_at: Optional[datetime.datetime] = None
    contest_reviewed_by_id: Optional[uuid.UUID] = None
    contest_note: str = ''

    @property
    def is_suspension(self) -> bool:
        return self.step in SUSPENSIONS

    @property
    def cancelled(self) -> bool:
        return self.cancelled_at is not None

    def active_at(self, now: datetime.datetime) -> bool:
        return self.is_suspension and not self.cancelled and self.starts_at <= now < self.ends_at

    def contestable_at(self, now: datetime.datetime, delay: datetime.timedelta) -> bool:
        return not self.cancelled and not self.contested_at and now <= self.created_at + delay

    def cancel(self, now: datetime.datetime) -> None:
        self.cancelled_at = now
        if self.is_suspension and self.ends_at > now:
            self.ends_at = max(now, self.starts_at)
