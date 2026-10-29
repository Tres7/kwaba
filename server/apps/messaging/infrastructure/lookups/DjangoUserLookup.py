import uuid
from typing import Dict, List, Optional

from apps.messaging.application.ports.UserLookup import UserInfo, UserLookup
from apps.users import api as users


class DjangoUserLookup(UserLookup):
    """Only contact point of messaging with the user model."""

    def _to_info(self, user) -> UserInfo:
        return UserInfo(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            avatar_url=user.avatar_url,
        )

    def get(self, user_id: uuid.UUID) -> Optional[UserInfo]:
        user = users.compte(user_id)
        return self._to_info(user) if user else None

    def get_many(self, user_ids: List[uuid.UUID]) -> Dict[uuid.UUID, UserInfo]:
        return {i: self._to_info(u) for i, u in users.comptes(user_ids).items()}
