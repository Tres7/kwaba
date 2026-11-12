from abc import ABC, abstractmethod

from apps.messaging.domain.entities.Sanction import Sanction


class SanctionNotifier(ABC):

    @abstractmethod
    def sanction_applied(self, sanction: Sanction) -> None:
        pass

    @abstractmethod
    def contest_reviewed(self, sanction: Sanction) -> None:
        pass
