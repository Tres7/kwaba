import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from apps.activity.domain.entities import Entry


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        pass


@dataclass(frozen=True)
class Person:
    id: uuid.UUID
    name: str
    email: str
    role: str


class PeopleLookup(ABC):
    @abstractmethod
    def people(self, ids) -> dict[uuid.UUID, Person]:
        pass

    @abstractmethod
    def matching(self, text: str) -> list[uuid.UUID]:
        pass


@dataclass(frozen=True)
class SearchQuery:
    text: str = ''
    actor_id: uuid.UUID | None = None
    ip: str = ''
    target_kind: str = ''
    target_id: str = ''
    actions: list[str] | None = None
    excluded_actions: list[str] = field(default_factory=list)
    start: datetime | None = None
    end: datetime | None = None
    before_id: int | None = None
    limit: int = 100


class EntryRepository(ABC):
    @abstractmethod
    def add(self, entry: Entry) -> None:
        pass

    @abstractmethod
    def search(self, query: SearchQuery, actor_ids: list[uuid.UUID]) -> list[Entry]:
        pass

    @abstractmethod
    def count_by_action(self, query: SearchQuery, actor_ids: list[uuid.UUID]) -> dict[str, int]:
        pass

    @abstractmethod
    def get(self, entry_id: int) -> Entry | None:
        pass

    @abstractmethod
    def hold(self, target_kind: str, target_id: str, on: bool) -> None:
        pass

    @abstractmethod
    def held(self, target_kind: str, target_id: str) -> bool:
        pass

    @abstractmethod
    def purge(self, before: datetime) -> int:
        pass
