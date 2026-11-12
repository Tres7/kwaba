import datetime
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from apps.messaging.domain.entities.Sanction import Sanction
from apps.messaging.domain.services.SanctionLadder import AppliedSuspension


class SanctionRepository(ABC):

    @abstractmethod
    def add(self, sanction: Sanction) -> Sanction:
        pass

    @abstractmethod
    def get(self, sanction_id: int) -> Optional[Sanction]:
        pass

    @abstractmethod
    def save(self, sanction: Sanction) -> None:
        pass

    @abstractmethod
    def for_report(self, report_id: int) -> List[Sanction]:
        pass

    @abstractmethod
    def for_user(self, user_id: uuid.UUID, limit: int) -> List[Sanction]:
        pass

    @abstractmethod
    def applied_suspensions(self, user_id: uuid.UUID) -> List[AppliedSuspension]:
        pass

    @abstractmethod
    def admin_decision_count(self, user_id: uuid.UUID) -> int:
        pass

    @abstractmethod
    def active_suspension_end(self, user_id: uuid.UUID, now: datetime.datetime) -> Optional[datetime.datetime]:
        pass
