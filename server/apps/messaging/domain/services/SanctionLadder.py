import datetime
from dataclasses import dataclass
from typing import List, Optional, Sequence

REMINDER = 'reminder'
FORMAL_WARNING = 'formal_warning'
SHORT_SUSPENSION = 'short_suspension'
LONG_SUSPENSION = 'long_suspension'
ADMIN_DECISION = 'admin_decision'
STEPS = (REMINDER, FORMAL_WARNING, SHORT_SUSPENSION, LONG_SUSPENSION, ADMIN_DECISION)
SUSPENSIONS = (SHORT_SUSPENSION, LONG_SUSPENSION)


@dataclass(frozen=True)
class LadderPolicy:
    window: datetime.timedelta = datetime.timedelta(days=30)
    warning_threshold: int = 3
    suspension_threshold: int = 5
    short_suspension: datetime.timedelta = datetime.timedelta(hours=24)
    long_suspension: datetime.timedelta = datetime.timedelta(days=7)


@dataclass(frozen=True)
class AppliedSuspension:
    step: str
    starts_at: datetime.datetime
    ends_at: datetime.datetime


@dataclass(frozen=True)
class LadderOutcome:
    step: str
    level: int
    starts_at: Optional[datetime.datetime] = None
    ends_at: Optional[datetime.datetime] = None


class _Replay:
    def __init__(self, policy: LadderPolicy, suspensions: Sequence[AppliedSuspension], now: datetime.datetime):
        self.policy = policy
        self.now = now
        self.pending = {step: sorted((s for s in suspensions if s.step == step), key=lambda s: s.starts_at)
                        for step in SUSPENSIONS}
        self.level = 0
        self.window: List[datetime.datetime] = []
        self.reference_end: Optional[datetime.datetime] = None
        self.new_suspension: Optional[AppliedSuspension] = None
        self.admin_decisions = 0

    def _suspend(self, step: str, duration: datetime.timedelta) -> None:
        if self.pending[step]:
            self.reference_end = self.pending[step].pop(0).ends_at
            return
        self.new_suspension = AppliedSuspension(step, self.now, self.now + duration)
        self.reference_end = self.new_suspension.ends_at

    def add(self, case: datetime.datetime) -> None:
        if self.level and case > self.reference_end + self.policy.window:
            self.level, self.window = 0, []
        if self.level == 0:
            self.window = [c for c in self.window if c > case - self.policy.window] + [case]
            if len(self.window) >= self.policy.suspension_threshold:
                self._suspend(SHORT_SUSPENSION, self.policy.short_suspension)
                self.level, self.window = 1, []
        elif self.level == 1 and case > self.reference_end:
            self._suspend(LONG_SUSPENSION, self.policy.long_suspension)
            self.level = 2
        elif self.level == 2 and case > self.reference_end:
            self.level, self.reference_end = 3, case
            self.admin_decisions += 1
        elif self.level == 3:
            self.reference_end = max(self.reference_end, case)
            self.admin_decisions += 1


def evaluate(cases: Sequence[datetime.datetime], suspensions: Sequence[AppliedSuspension],
             recorded_admin_decisions: int, policy: LadderPolicy, now: datetime.datetime) -> LadderOutcome:
    replay = _Replay(policy, suspensions, now)
    for case in sorted(cases):
        replay.add(case)
    if replay.new_suspension:
        return LadderOutcome(replay.new_suspension.step, replay.level,
                             replay.new_suspension.starts_at, replay.new_suspension.ends_at)
    if replay.admin_decisions > recorded_admin_decisions:
        return LadderOutcome(ADMIN_DECISION, replay.level)
    if replay.level == 0 and len(replay.window) >= policy.warning_threshold:
        return LadderOutcome(FORMAL_WARNING, replay.level)
    return LadderOutcome(REMINDER, replay.level)
