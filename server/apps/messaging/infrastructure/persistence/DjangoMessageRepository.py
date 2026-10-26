import uuid
from typing import Dict, List, Optional

from django.db.models import Count, Q

from apps.messaging.domain.entities.Conversation import Conversation
from apps.messaging.domain.entities.Message import Message
from apps.messaging.domain.repositories.MessageRepository import MessageRepository
from apps.messaging.infrastructure.persistence.models import MessageModel


class DjangoMessageRepository(MessageRepository):

    def _to_entity(self, model: MessageModel) -> Message:
        return Message(
            id=model.id,
            conversation_id=model.conversation_id,
            sender_id=model.sender_id,
            content=model.content,
            masked=model.masque,
            created_at=model.created_at,
        )

    def add(self, message: Message) -> Message:
        model = MessageModel.objects.create(
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            content=message.content,
            masque=message.masked,
            created_at=message.created_at,
        )
        return self._to_entity(model)

    def list(self, conversation_id: uuid.UUID, after_id: Optional[int], limit: int) -> List[Message]:
        qs = MessageModel.objects.filter(conversation_id=conversation_id)
        if after_id is not None:
            return [self._to_entity(m) for m in qs.filter(id__gt=after_id).order_by('id')[:limit]]
        latest = list(qs.order_by('-id')[:limit])
        latest.reverse()
        return [self._to_entity(m) for m in latest]

    def latest_id(self, conversation_id: uuid.UUID) -> Optional[int]:
        return (
            MessageModel.objects.filter(conversation_id=conversation_id)
            .order_by('-id').values_list('id', flat=True).first()
        )

    def has_unread_for(self, conversation: Conversation, user_id: uuid.UUID) -> bool:
        return (
            MessageModel.objects
            .filter(conversation_id=conversation.id, id__gt=conversation.last_read_id_for(user_id))
            .exclude(sender_id=user_id)
            .exists()
        )

    def last_messages(self, conversation_ids: List[uuid.UUID]) -> Dict[uuid.UUID, Message]:
        # DISTINCT ON (PostgreSQL): the most recent message of each thread, in one query
        qs = (
            MessageModel.objects.filter(conversation_id__in=conversation_ids)
            .order_by('conversation_id', '-id')
            .distinct('conversation_id')
        )
        return {m.conversation_id: self._to_entity(m) for m in qs}

    def unread_counts(self, user_id: uuid.UUID, conversations: List[Conversation]) -> Dict[uuid.UUID, int]:
        if not conversations:
            return {}
        # Each thread has its own cursor: one condition per thread, grouped into a single query
        condition = Q()
        for c in conversations:
            condition |= Q(conversation_id=c.id, id__gt=c.last_read_id_for(user_id))
        rows = (
            MessageModel.objects.filter(condition)
            .exclude(sender_id=user_id)
            .values('conversation_id')
            .annotate(unread=Count('id'))
        )
        return {row['conversation_id']: row['unread'] for row in rows}
