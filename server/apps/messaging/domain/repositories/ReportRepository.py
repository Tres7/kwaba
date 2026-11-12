import datetime
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

from apps.messaging.domain.entities.MessageReport import MessageReport


class ReportRepository(ABC):

    @abstractmethod
    def add(self, report: MessageReport) -> MessageReport:
        pass

    @abstractmethod
    def get(self, report_id: int) -> Optional[MessageReport]:
        pass

    @abstractmethod
    def find(self, reporter_id: uuid.UUID, message_id: int) -> Optional[MessageReport]:
        pass

    @abstractmethod
    def save(self, report: MessageReport) -> None:
        pass

    @abstractmethod
    def confirmed_case_dates(self, author_id: uuid.UUID) -> List[datetime.datetime]:
        pass

    @abstractmethod
    def rejected_count_since(self, reporter_id: uuid.UUID, since: datetime.datetime) -> int:
        pass
