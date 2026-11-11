import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Tuple

OFF, OBSERVE, ENFORCE = 'off', 'observe', 'enforce'
ALLOW, WARN, BLOCK = 'allow', 'warn', 'block'
REFUSAL, SIMULATED, WARNING_IGNORED = 'refusal', 'simulated', 'warning_ignored'


@dataclass(frozen=True)
class ModerationVerdict:
    level: str = ALLOW
    categories: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def flagged(self) -> bool:
        return self.level != ALLOW


class ModerationGuard(ABC):

    @abstractmethod
    def mode(self) -> str:
        pass

    @abstractmethod
    def screen(self, text: str) -> ModerationVerdict:
        pass

    @abstractmethod
    def record(self, user_id: uuid.UUID, conversation_id: uuid.UUID, kind: str, verdict: ModerationVerdict,
               content: str) -> None:
        pass

    @abstractmethod
    def record_false_positive(self, user_id: uuid.UUID, conversation_id: uuid.UUID, verdict: ModerationVerdict,
                              content: str) -> None:
        pass


class DisabledModerationGuard(ModerationGuard):

    def mode(self) -> str:
        return OFF

    def screen(self, text: str) -> ModerationVerdict:
        return ModerationVerdict()

    def record(self, user_id, conversation_id, kind, verdict, content) -> None:
        pass

    def record_false_positive(self, user_id, conversation_id, verdict, content) -> None:
        pass
