from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List
import uuid


@dataclass
class Screening:
    """Result of filtering a message: text to save (contact details hidden) and detected elements."""
    content: str
    masked: bool = False
    findings: List[object] = field(default_factory=list)


class ContactGuard(ABC):
    """Anti-bypass: hides contact details (phone, email, links…) and reports the attempts."""

    @abstractmethod
    def screen(self, text: str) -> Screening:
        pass

    @abstractmethod
    def report(self, sender_id: uuid.UUID, conversation_id: uuid.UUID, screening: Screening) -> None:
        pass


class PassThroughContactGuard(ContactGuard):
    """Without filtering (domain tests)."""

    def screen(self, text: str) -> Screening:
        return Screening(content=text)

    def report(self, sender_id, conversation_id, screening) -> None:
        pass
