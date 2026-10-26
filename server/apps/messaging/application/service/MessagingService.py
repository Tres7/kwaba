import datetime
import logging
from typing import List, Optional, Tuple
import uuid

from apps.messaging.application.dto.dto import (
    ConversationSummaryDTO,
    HebergementSummaryDTO,
    MessageDTO,
    ParticipantDTO,
)
from apps.messaging.application.events.NewMessageEmailRequested import NewMessageEmailRequested
from apps.messaging.application.ports.BookingLookup import BookingLookup, EveryoneBooked
from apps.messaging.application.ports.ContactGuard import ContactGuard, PassThroughContactGuard
from apps.messaging.application.ports.HebergementLookup import HebergementLookup
from apps.messaging.application.ports.NotificationOutbox import NotificationOutbox
from apps.messaging.application.ports.TransactionManager import TransactionManager
from apps.messaging.application.ports.UserLookup import UserLookup
from apps.messaging.domain.entities.Conversation import Conversation
from apps.messaging.domain.entities.Message import Message
from apps.messaging.domain.exceptions import (
    ConversationAlreadyExistsException,
    ConversationNotFoundException,
    HebergementNotFoundException,
    NotParticipantException,
)
from apps.messaging.domain.repositories.ConversationRepository import ConversationRepository
from apps.messaging.domain.repositories.MessageRepository import MessageRepository

logger = logging.getLogger(__name__)


class MessagingService:
    """Traveller ↔ host messaging.

    Anti-bypass: everything goes through the messaging, before as after the booking.
    - contact details (phone, email, links, social networks) are hidden in every message, and the
      attempts reported to the administrators (ContactGuard);
    - as long as the traveller has no paid booking for the listing, they stay anonymous to the host ("Voyageur",
      without name nor photo): a host cannot identify them to offer an arrangement outside the site.
    """

    ANONYMOUS_GUEST = 'Voyageur'
    INITIAL_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 100

    def __init__(
        self,
        conversations: ConversationRepository,
        messages: MessageRepository,
        hebergements: HebergementLookup,
        users: UserLookup,
        outbox: NotificationOutbox,
        tx: TransactionManager,
        email_delay_seconds: int = 60,
        guard: Optional[ContactGuard] = None,
        bookings: Optional[BookingLookup] = None,
    ):
        self._conversations = conversations
        self._messages = messages
        self._hebergements = hebergements
        self._users = users
        self._outbox = outbox
        self._tx = tx
        self._email_delay = datetime.timedelta(seconds=email_delay_seconds)
        self._guard = guard or PassThroughContactGuard()
        self._bookings = bookings or EveryoneBooked()

    def start_conversation(self, user_id: uuid.UUID, hebergement_id: uuid.UUID) -> Tuple[ConversationSummaryDTO, bool]:
        """Idempotent: returns the existing thread if there is already one. The boolean tells a creation."""
        hebergement = self._hebergements.get(hebergement_id)
        if hebergement is None:
            raise HebergementNotFoundException(str(hebergement_id))
        return self._open(hebergement, guest_id=user_id, viewer_id=user_id)

    def open_as_host(
        self, host_id: uuid.UUID, hebergement_id: uuid.UUID, guest_id: uuid.UUID,
    ) -> Tuple[ConversationSummaryDTO, bool]:
        """The host opens (or finds) the thread with a traveller of their listing.

        The "this traveller did book this listing" check is made by the caller.
        """
        hebergement = self._hebergements.get(hebergement_id)
        if hebergement is None:
            raise HebergementNotFoundException(str(hebergement_id))
        if hebergement.host_id != host_id:
            raise NotParticipantException(str(hebergement_id))
        return self._open(hebergement, guest_id=guest_id, viewer_id=host_id)

    def _open(self, hebergement, guest_id: uuid.UUID, viewer_id: uuid.UUID) -> Tuple[ConversationSummaryDTO, bool]:
        # Raises CannotContactOwnHebergementException if the traveller is the host
        conversation = Conversation.start(hebergement.id, guest_id, hebergement.host_id)

        existing = self._conversations.find_by_hebergement_and_guest(hebergement.id, guest_id)
        if existing:
            return self._summaries([existing], viewer_id)[0], False

        try:
            created = self._conversations.create(conversation)
        except ConversationAlreadyExistsException:
            # Concurrent creation: the other request won, its thread is returned
            existing = self._conversations.find_by_hebergement_and_guest(hebergement.id, guest_id)
            if existing is None:
                # Integrity violation of another kind (listing deleted in the meantime)
                raise HebergementNotFoundException(str(hebergement.id))
            return self._summaries([existing], viewer_id)[0], False

        return self._summaries([created], viewer_id)[0], True

    def list_conversations(self, user_id: uuid.UUID) -> List[ConversationSummaryDTO]:
        return self._summaries(self._conversations.list_for_user(user_id), user_id)

    def unread_total(self, user_id: uuid.UUID) -> int:
        """Total number of unread messages, all threads together (navbar badge)."""
        conversations = self._conversations.list_for_user(user_id)
        return sum(self._messages.unread_counts(user_id, conversations).values())

    def get_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> ConversationSummaryDTO:
        conversation = self._participant_conversation(conversation_id, user_id)
        return self._summaries([conversation], user_id)[0]

    def get_messages(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        after_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[MessageDTO]:
        conversation = self._participant_conversation(conversation_id, user_id)
        page_size = min(limit or self.INITIAL_PAGE_SIZE, self.MAX_PAGE_SIZE)
        messages = self._messages.list(conversation.id, after_id, page_size)
        return [MessageDTO.from_entity(m, user_id) for m in messages]

    def send_message(self, user_id: uuid.UUID, conversation_id: uuid.UUID, content: str) -> MessageDTO:
        Message.compose(conversation_id, user_id, content)  # validation of the typed text (empty, length)
        screening = self._guard.screen(content)
        message = Message.compose(conversation_id, user_id, screening.content)
        message.masked = screening.masked

        with self._tx.atomic():
            # The lock serialises the sending in a thread: message ids are therefore
            # committed in order (reliable cursor for ?after=), and the 0→1 decision cannot
            # be taken twice in parallel.
            conversation = self._conversations.find_by_id_for_update(conversation_id)
            if conversation is None or not conversation.is_participant(user_id):
                raise ConversationNotFoundException(str(conversation_id))

            recipient_id = conversation.other_participant(user_id)
            first_unread_for_recipient = not self._messages.has_unread_for(conversation, recipient_id)

            saved = self._messages.add(message)
            conversation.record_message(user_id, saved.id, saved.created_at)
            self._conversations.save(conversation)
            if screening.findings:
                self._guard.report(user_id, conversation.id, screening)

            if first_unread_for_recipient:
                self._schedule_new_message_email(conversation, saved, recipient_id)

        return MessageDTO.from_entity(saved, user_id)

    def mark_as_read(self, user_id: uuid.UUID, conversation_id: uuid.UUID, up_to_id: Optional[int] = None) -> int:
        """Moves the read cursor forward (up to the last message by default). Returns the cursor."""
        with self._tx.atomic():
            conversation = self._conversations.find_by_id_for_update(conversation_id)
            if conversation is None or not conversation.is_participant(user_id):
                raise ConversationNotFoundException(str(conversation_id))

            latest_id = self._messages.latest_id(conversation.id)
            if latest_id is not None:
                target = latest_id if up_to_id is None else min(up_to_id, latest_id)
                conversation.mark_read(user_id, target)
                self._conversations.save(conversation)

            return conversation.last_read_id_for(user_id)

    def _schedule_new_message_email(self, conversation: Conversation, message: Message, recipient_id: uuid.UUID) -> None:
        """Writes the notification into the outbox, in the sending transaction.
        The relay will publish it after the delay, if the recipient has not read in the meantime."""
        people = self._users.get_many([recipient_id, message.sender_id])
        recipient = people.get(recipient_id)
        sender = people.get(message.sender_id)
        hebergement = self._hebergements.get(conversation.hebergement_id)
        anonymous_sender = message.sender_id == conversation.guest_id and not self._is_booked(conversation)

        if recipient is None or not recipient.email:
            logger.warning(
                "Notification non planifiée : destinataire sans email (conversation=%s, recipient=%s)",
                conversation.id, recipient_id,
            )
            return

        self._outbox.schedule(
            event_type=NewMessageEmailRequested.EVENT_NAME,
            conversation_id=conversation.id,
            message_id=message.id,
            recipient_id=recipient_id,
            payload={
                'conversation_id': str(conversation.id),
                'recipient_email': recipient.email,
                'recipient_first_name': recipient.first_name,
                'sender_first_name': 'Un voyageur' if anonymous_sender else (sender.first_name if sender else ''),
                'hebergement_name': hebergement.name if hebergement else '',
                'message_preview': message.preview(),
            },
            available_at=message.created_at + self._email_delay,
        )

    def _is_booked(self, conversation: Conversation) -> bool:
        pair = (conversation.hebergement_id, conversation.guest_id)
        return pair in self._bookings.booked([pair])

    def _participant_conversation(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation:
        # A non-participant gets the same response as a missing thread: its existence is not revealed
        conversation = self._conversations.find_by_id(conversation_id)
        if conversation is None or not conversation.is_participant(user_id):
            raise ConversationNotFoundException(str(conversation_id))
        return conversation

    def _summaries(self, conversations: List[Conversation], user_id: uuid.UUID) -> List[ConversationSummaryDTO]:
        if not conversations:
            return []

        # Constant number of queries, whatever the number of threads
        ids = [c.id for c in conversations]
        last_messages = self._messages.last_messages(ids)
        unread = self._messages.unread_counts(user_id, conversations)
        hebergements = self._hebergements.get_many(list({c.hebergement_id for c in conversations}))
        others = self._users.get_many(list({c.other_participant(user_id) for c in conversations}))
        booked = self._bookings.booked({(c.hebergement_id, c.guest_id) for c in conversations})

        summaries = []
        for c in conversations:
            heb = hebergements.get(c.hebergement_id)
            other = others.get(c.other_participant(user_id))
            last = last_messages.get(c.id)
            is_booked = (c.hebergement_id, c.guest_id) in booked
            # On the host's side, anonymous traveller as long as they have not paid
            anonymous = other is not None and c.role_of(user_id) == 'host' and not is_booked
            summaries.append(ConversationSummaryDTO(
                id=c.id,
                my_role=c.role_of(user_id),
                hebergement=HebergementSummaryDTO(
                    id=heb.id, name=heb.name, city=heb.city, image_url=heb.image_url,
                ) if heb else None,
                other_participant=(
                    ParticipantDTO(id=other.id, first_name=self.ANONYMOUS_GUEST, last_name='', avatar_url=None) if anonymous
                    else ParticipantDTO(id=other.id, first_name=other.first_name,
                                        last_name=other.last_name, avatar_url=other.avatar_url)
                ) if other else None,
                last_message=MessageDTO.from_entity(last, user_id) if last else None,
                unread_count=unread.get(c.id, 0),
                last_message_at=c.last_message_at,
                booked=is_booked,
            ))
        return summaries
