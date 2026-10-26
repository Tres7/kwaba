# this repository defines how messages can be saved
# it defines methods without body. Infrastructure will make the body
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import uuid

from apps.messaging.domain.entities.Conversation import Conversation
from apps.messaging.domain.entities.Message import Message


class MessageRepository(ABC):

    @abstractmethod
    def add(self, message: Message) -> Message:
        """Saves the message and returns the entity with its sequential id."""
        pass

    @abstractmethod
    def list(self, conversation_id: uuid.UUID, after_id: Optional[int], limit: int) -> List[Message]:
        """Messages by ascending id. Without after_id: the `limit` most recent ones."""
        pass

    @abstractmethod
    def latest_id(self, conversation_id: uuid.UUID) -> Optional[int]:
        pass

    @abstractmethod
    def has_unread_for(self, conversation: Conversation, user_id: uuid.UUID) -> bool:
        pass

    @abstractmethod
    def last_messages(self, conversation_ids: List[uuid.UUID]) -> Dict[uuid.UUID, Message]:
        pass

    @abstractmethod
    def unread_counts(self, user_id: uuid.UUID, conversations: List[Conversation]) -> Dict[uuid.UUID, int]:
        pass
