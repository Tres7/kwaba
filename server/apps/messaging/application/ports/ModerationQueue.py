import uuid
from abc import ABC, abstractmethod

from apps.messaging.domain.entities.MessageReport import MessageReport
from apps.messaging.domain.entities.Sanction import Sanction


class ModerationQueue(ABC):

    @abstractmethod
    def report_received(self, report: MessageReport, excerpt: str) -> None:
        pass

    @abstractmethod
    def report_closed(self, report: MessageReport) -> None:
        pass

    @abstractmethod
    def sanction_applied(self, sanction: Sanction) -> None:
        pass

    @abstractmethod
    def contest_received(self, sanction: Sanction) -> None:
        pass

    @abstractmethod
    def contest_closed(self, sanction: Sanction) -> None:
        pass

    @abstractmethod
    def abusive_reporter(self, reporter_id: uuid.UUID, rejected_count: int) -> None:
        pass

    @abstractmethod
    def active_admin_ids(self) -> list[uuid.UUID]:
        pass
