# this repository defines how conversations can be saved
# it defines methods without body. Infrastructure will make the body
from abc import ABC, abstractmethod
from typing import List, Optional
import uuid

from apps.messaging.domain.entities.Conversation import Conversation


class ConversationRepository(ABC):

    @abstractmethod
    def find_by_id(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        pass

    @abstractmethod
    def find_by_id_for_update(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        """Locks the thread until the end of the current transaction."""
        pass

    @abstractmethod
    def find_by_hebergement_and_guest(self, hebergement_id: uuid.UUID, guest_id: uuid.UUID) -> Optional[Conversation]:
        pass

    @abstractmethod
    def create(self, conversation: Conversation) -> Conversation:
        """Raises ConversationAlreadyExistsException if the thread already exists."""
        pass

    @abstractmethod
    def save(self, conversation: Conversation) -> None:
        pass

    @abstractmethod
    def list_for_user(self, user_id: uuid.UUID) -> List[Conversation]:
        """Threads of the participant, from the most recently active to the oldest."""
        pass
