import uuid
from typing import List, Optional

from django.db import IntegrityError, transaction
from django.db.models import Q

from apps.messaging.domain.entities.Conversation import Conversation
from apps.messaging.domain.exceptions import ConversationAlreadyExistsException
from apps.messaging.domain.repositories.ConversationRepository import ConversationRepository
from apps.messaging.infrastructure.persistence.models import ConversationModel


class DjangoConversationRepository(ConversationRepository):

    def _to_entity(self, model: ConversationModel) -> Conversation:
        return Conversation(
            id=model.id,
            hebergement_id=model.hebergement_id,
            guest_id=model.guest_id,
            host_id=model.host_id,
            guest_last_read_id=model.guest_last_read_id,
            host_last_read_id=model.host_last_read_id,
            created_at=model.created_at,
            last_message_at=model.last_message_at,
        )

    def find_by_id(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        model = ConversationModel.objects.filter(id=conversation_id).first()
        return self._to_entity(model) if model else None

    def find_by_id_for_update(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        model = ConversationModel.objects.select_for_update().filter(id=conversation_id).first()
        return self._to_entity(model) if model else None

    def find_by_hebergement_and_guest(self, hebergement_id: uuid.UUID, guest_id: uuid.UUID) -> Optional[Conversation]:
        model = ConversationModel.objects.filter(hebergement_id=hebergement_id, guest_id=guest_id).first()
        return self._to_entity(model) if model else None

    def create(self, conversation: Conversation) -> Conversation:
        try:
            # Savepoint: an IntegrityError must not break a possible enclosing transaction
            with transaction.atomic():
                model = ConversationModel.objects.create(
                    id=conversation.id,
                    hebergement_id=conversation.hebergement_id,
                    guest_id=conversation.guest_id,
                    host_id=conversation.host_id,
                    guest_last_read_id=conversation.guest_last_read_id,
                    host_last_read_id=conversation.host_last_read_id,
                    created_at=conversation.created_at,
                    last_message_at=conversation.last_message_at,
                )
        except IntegrityError as e:
            raise ConversationAlreadyExistsException() from e
        return self._to_entity(model)

    def save(self, conversation: Conversation) -> None:
        ConversationModel.objects.filter(id=conversation.id).update(
            guest_last_read_id=conversation.guest_last_read_id,
            host_last_read_id=conversation.host_last_read_id,
            last_message_at=conversation.last_message_at,
        )

    def list_for_user(self, user_id: uuid.UUID) -> List[Conversation]:
        qs = ConversationModel.objects.filter(Q(guest_id=user_id) | Q(host_id=user_id)).order_by('-last_message_at')
        return [self._to_entity(m) for m in qs]
