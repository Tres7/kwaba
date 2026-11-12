import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

CONFIRMED, CANCELLED, DONE = 'confirmed', 'cancelled', 'done'
ACTIVE = (CONFIRMED, DONE)
ORIGIN_HOST, ORIGIN_PHONE = 'host', 'phone'
BLOCK, EXTRA = 'block', 'extra'


@dataclass(frozen=True)
class WeeklySlot:
    weekday: int
    start: time
    end: time


@dataclass(frozen=True)
class AvailabilityException:
    day: date
    kind: str
    start: time | None = None
    end: time | None = None
    id: int | None = None


@dataclass(frozen=True)
class Target:
    id: str
    title: str
    latitude: float | None = None
    longitude: float | None = None


@dataclass
class Agenda:
    agent_id: uuid.UUID
    id: uuid.UUID | None = None
    timezone: str = 'Africa/Lome'
    cities: list[str] = field(default_factory=list)
    weekly_slots: list[WeeklySlot] = field(default_factory=list)
    exceptions: list[AvailabilityException] = field(default_factory=list)
    day_limits: dict[date, int] = field(default_factory=dict)
    ics_token: str = ''
    availability_reminder_at: datetime | None = None

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@dataclass
class Appointment:
    agenda_id: uuid.UUID
    agent_id: uuid.UUID
    requester_id: uuid.UUID
    targets: list[Target]
    city: str
    start: datetime
    end: datetime
    blocked_until: datetime
    id: uuid.UUID | None = None
    address: str = ''
    status: str = CONFIRMED
    origin: str = ORIGIN_HOST
    waiting_since: datetime | None = None
    created_at: datetime | None = None
    on_the_way_at: datetime | None = None
    done_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancelled_by: str = ''
    cancellation_reason: str = ''
    closing_reason: str = ''
    post_check: bool = False
    sequence: int = 0
    host_reminder_at: datetime | None = None
    alert_at: datetime | None = None

    @property
    def title(self) -> str:
        if len(self.targets) == 1:
            return self.targets[0].title
        return f"{self.targets[0].title} + {len(self.targets) - 1}"

    @property
    def active(self) -> bool:
        if self.status == DONE:
            return self.done_at is None or self.done_at >= self.start
        return self.status == CONFIRMED
