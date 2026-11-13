import logging
import uuid
from dataclasses import replace
from datetime import datetime, time, timedelta

from apps.activity.domain import catalogue
from apps.activity.domain.entities import Entry, Target
from apps.activity.domain.retention import purge_before

from .ports import Clock, EntryRepository, PeopleLookup, SearchQuery

logger = logging.getLogger('apps.activity')

BLOCKING_ACTIONS = ['connexion_bloquee', 'code_bloque']


class ActivityService:
    def __init__(self, *, entries: EntryRepository, people: PeopleLookup, clock: Clock):
        self.entries = entries
        self.people = people
        self.clock = clock

    def record(self, action: str, *, actor=None, actor_email: str = '', ip: str | None = None,
               target: Target | None = None, details: dict | None = None) -> None:
        details = dict(details or {})
        try:
            self.entries.add(Entry(
                action=action,
                created_at=self.clock.now(),
                actor_id=getattr(actor, 'pk', actor),
                actor_email=(actor_email or getattr(actor, 'email', '') or '')[:254],
                actor_role=(getattr(actor, 'role', '') or '')[:20],
                ip=ip,
                target=target or catalogue.resolve_target(action, details),
                details=details,
            ))
        except Exception:
            logger.exception("Activity log: entry not written (%s)", action)

    def _actor_ids(self, query: SearchQuery) -> list:
        return self.people.matching(query.text) if query.text else []

    def search(self, query: SearchQuery) -> tuple[list[Entry], dict]:
        found = self.entries.search(query, self._actor_ids(query))
        return found, self.people.people({e.actor_id for e in found if e.actor_id} | {
            _uuid(e.target.id) for e in found if e.target and e.target.kind == 'account' and _uuid(e.target.id)})

    def counts(self, query: SearchQuery) -> dict[str, int]:
        by_action = self.entries.count_by_action(replace(query, actions=None, before_id=None), self._actor_ids(query))
        totals = {code: 0 for code in catalogue.CATEGORIES}
        for action, count in by_action.items():
            totals[catalogue.spec(action).category] += count
        return totals

    def today(self) -> dict[str, int]:
        now = self.clock.now()
        start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
        window = SearchQuery(start=start, end=start + timedelta(days=1))
        by_action = self.entries.count_by_action(window, [])
        return {
            'sensitive': sum(n for a, n in by_action.items() if catalogue.spec(a).level == catalogue.SENSITIVE),
            'blocked': sum(by_action.get(a, 0) for a in BLOCKING_ACTIONS),
        }

    def get(self, entry_id: int) -> tuple[Entry | None, dict]:
        entry = self.entries.get(entry_id)
        if entry is None:
            return None, {}
        ids = {entry.actor_id} if entry.actor_id else set()
        if entry.target and entry.target.kind == 'account' and _uuid(entry.target.id):
            ids.add(_uuid(entry.target.id))
        return entry, self.people.people(ids)

    def hold(self, target_kind: str, target_id: str, on: bool) -> None:
        self.entries.hold(target_kind, str(target_id), on)

    def purge(self) -> int:
        return self.entries.purge(purge_before(self.clock.now()))


def _uuid(value):
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None

