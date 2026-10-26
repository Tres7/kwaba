from abc import ABC, abstractmethod
from typing import ContextManager


class TransactionManager(ABC):
    """Delimits a transaction: locks and writes (message, cursors, outbox) are committed together."""

    @abstractmethod
    def atomic(self) -> ContextManager:
        pass
