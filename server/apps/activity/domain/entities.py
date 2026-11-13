import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Target:
    kind: str
    id: str
    label: str = ''


@dataclass
class Entry:
    action: str
    created_at: datetime
    id: int | None = None
    actor_id: uuid.UUID | None = None
    actor_email: str = ''
    actor_role: str = ''
    ip: str | None = None
    target: Target | None = None
    details: dict = field(default_factory=dict)
    legacy: bool = False
    hold: bool = False
