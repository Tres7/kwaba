import uuid
from typing import Dict, List, Optional

from django.contrib.auth import get_user_model

from apps.messaging.application.ports.UserLookup import UserInfo, UserLookup


class DjangoUserLookup(UserLookup):
    """Only contact point of messaging with the user model."""

    def _to_info(self, user) -> UserInfo:
        return UserInfo(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            avatar_url=user.avatar.url if user.avatar else None,
        )

    def get(self, user_id: uuid.UUID) -> Optional[UserInfo]:
        user = get_user_model().objects.filter(id=user_id).first()
        return self._to_info(user) if user else None

    def get_many(self, user_ids: List[uuid.UUID]) -> Dict[uuid.UUID, UserInfo]:
        users = get_user_model().objects.filter(id__in=user_ids)
        return {u.id: self._to_info(u) for u in users}
