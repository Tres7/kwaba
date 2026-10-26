# Registers the persistence models with Django (same convention as apps/users/models.py).
# Without this import, the ORM ignores these models at startup: cascading deletions
# (user, listing) fail on the messaging foreign keys.
from apps.messaging.infrastructure.persistence.models import (
    ConversationModel,
    MessageModel,
    NotificationOutboxModel,
)

__all__ = ["ConversationModel", "MessageModel", "NotificationOutboxModel"]
