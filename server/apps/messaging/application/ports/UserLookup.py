from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
import uuid


@dataclass
class UserInfo:
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    avatar_url: Optional[str]


class UserLookup(ABC):
    """Read access to the users context, without depending on its models."""

    @abstractmethod
    def get(self, user_id: uuid.UUID) -> Optional[UserInfo]:
        pass

    @abstractmethod
    def get_many(self, user_ids: List[uuid.UUID]) -> Dict[uuid.UUID, UserInfo]:
        pass
