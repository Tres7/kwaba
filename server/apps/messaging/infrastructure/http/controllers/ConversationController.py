import uuid
from typing import Optional

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.messaging.application.dto.dto import ConversationSummaryDTO, MessageDTO
from apps.messaging.domain.exceptions import (
    CannotContactOwnHebergementException,
    ConversationNotFoundException,
    HebergementNotFoundException,
    InvalidMessageException,
    NotParticipantException,
)
from apps.messaging.infrastructure.container import messaging_service
from apps.messaging.infrastructure.http.permissions import IsVerified
from apps.messaging.infrastructure.lookups.DjangoBookingLookup import DjangoBookingLookup
from apps.messaging.infrastructure.lookups.DjangoHebergementLookup import DjangoHebergementLookup


def _parse_uuid(value) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def _parse_positive_int(value) -> Optional[int]:
    try:
        number = int(value)
    except (ValueError, TypeError):
        return None
    return number if number >= 0 else None


def _message_json(dto: MessageDTO) -> dict:
    return {
        'id': dto.id,
        'conversation_id': str(dto.conversation_id),
        'sender_id': str(dto.sender_id),
        'content': dto.content,
        'created_at': dto.created_at,
        'is_own': dto.is_own,
        'masked': dto.masked,
    }


def _conversation_json(dto: ConversationSummaryDTO) -> dict:
    return {
        'id': str(dto.id),
        'my_role': dto.my_role,
        'hebergement': {
            'id': str(dto.hebergement.id),
            'name': dto.hebergement.name,
            'city': dto.hebergement.city,
            'image_url': dto.hebergement.image_url,
        } if dto.hebergement else None,
        'other_participant': {
            'id': str(dto.other_participant.id),
            'first_name': dto.other_participant.first_name,
            'last_name': dto.other_participant.last_name,
            'avatar_url': dto.other_participant.avatar_url,
        } if dto.other_participant else None,
        'last_message': _message_json(dto.last_message) if dto.last_message else None,
        'unread_count': dto.unread_count,
        'last_message_at': dto.last_message_at,
        'booked': dto.booked,
    }


def _not_found(e: Exception) -> Response:
    return Response({'detail': str(e)}, status=status.HTTP_404_NOT_FOUND)


class WriteGuardsMixin:
    """Read: signed-in user. Write (POST): verified email + throttle of the view's scope.
    GETs (polling) are not throttled."""

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsVerified()]
        return [IsAuthenticated()]

    def get_throttles(self):
        if self.request.method == 'POST':
            return [ScopedRateThrottle()]
        return []


class ConversationListCreateView(WriteGuardsMixin, APIView):
    throttle_scope = 'messaging_conversation_create'

    def get(self, request):
        conversations = messaging_service().list_conversations(request.user.id)
        return Response({
            'results': [_conversation_json(c) for c in conversations],
            'count': len(conversations),
        })

    def post(self, request):
        hebergement_id = _parse_uuid(request.data.get('hebergement_id'))
        if hebergement_id is None:
            return Response({'detail': 'hebergement_id invalide ou manquant.'}, status=status.HTTP_400_BAD_REQUEST)

        # Listing not verified yet or hidden: its host cannot be contacted yet
        if not DjangoHebergementLookup().is_published(hebergement_id):
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            conversation, created = messaging_service().start_conversation(request.user.id, hebergement_id)
        except HebergementNotFoundException as e:
            return _not_found(e)
        except CannotContactOwnHebergementException as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

        return Response(
            _conversation_json(conversation),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ConversationWithGuestView(WriteGuardsMixin, APIView):
    """The host opens (or finds) the thread with the traveller of one of their bookings."""
    throttle_scope = 'messaging_conversation_create'

    def post(self, request):
        reservation_id = _parse_uuid(request.data.get('reservation_id'))
        if reservation_id is None:
            return Response({'detail': 'reservation_id invalide ou manquant.'}, status=status.HTTP_400_BAD_REQUEST)

        # Anti-abuse: a host can only write to a traveller who booked AND paid one of their listings
        reservation = DjangoBookingLookup().confirmed_for_host(reservation_id, request.user.id)
        if reservation is None:
            return Response({'detail': 'Réservation introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        hebergement_id, guest_id = reservation
        try:
            conversation, created = messaging_service().open_as_host(request.user.id, hebergement_id, guest_id)
        except HebergementNotFoundException as e:
            return _not_found(e)
        except (CannotContactOwnHebergementException, NotParticipantException) as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

        return Response(
            _conversation_json(conversation),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'unread_count': messaging_service().unread_total(request.user.id)})


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        try:
            conversation = messaging_service().get_conversation(request.user.id, conversation_id)
        except ConversationNotFoundException as e:
            return _not_found(e)
        return Response(_conversation_json(conversation))


class ConversationMessagesView(WriteGuardsMixin, APIView):
    throttle_scope = 'messaging_message_send'

    def get(self, request, conversation_id):
        after_raw = request.query_params.get('after')
        limit_raw = request.query_params.get('limit')
        after_id = _parse_positive_int(after_raw) if after_raw is not None else None
        limit = _parse_positive_int(limit_raw) if limit_raw is not None else None
        if (after_raw is not None and after_id is None) or (limit_raw is not None and not limit):
            return Response({'detail': 'Paramètres after/limit invalides.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            messages = messaging_service().get_messages(request.user.id, conversation_id, after_id, limit)
        except ConversationNotFoundException as e:
            return _not_found(e)
        return Response({'results': [_message_json(m) for m in messages]})

    def post(self, request, conversation_id):
        try:
            message = messaging_service().send_message(
                request.user.id, conversation_id, request.data.get('content', ''),
            )
        except ConversationNotFoundException as e:
            return _not_found(e)
        except InvalidMessageException as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_message_json(message), status=status.HTTP_201_CREATED)


class ConversationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        up_to_raw = request.data.get('up_to_id')
        up_to_id = _parse_positive_int(up_to_raw) if up_to_raw is not None else None
        if up_to_raw is not None and up_to_id is None:
            return Response({'detail': 'up_to_id invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            last_read_id = messaging_service().mark_as_read(request.user.id, conversation_id, up_to_id)
        except ConversationNotFoundException as e:
            return _not_found(e)
        return Response({'last_read_id': last_read_id})
