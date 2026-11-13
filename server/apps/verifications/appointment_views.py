from zoneinfo import ZoneInfo

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.agenda import api as agenda
from apps.activity import api as activity
from apps.users import api as users

from . import appointments
from .views import EstVerificateur


class IsHost(IsAuthenticated):
    message = "Réservé aux hôtes."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and users.hote_ou_candidat(request.user)


class IsAdmin(EstVerificateur):
    message = "Réservé aux administrateurs."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'


def _start(value):
    moment = parse_datetime(str(value or ''))
    if moment is None:
        return None
    if timezone.is_naive(moment):
        moment = moment.replace(tzinfo=ZoneInfo(agenda.DEFAULT_TIMEZONE))
    return moment


def _ids(value) -> list[str]:
    if isinstance(value, str):
        value = value.split(',')
    return [str(v).strip() for v in (value or []) if str(v).strip()]


def _refused(exc: appointments.AppointmentError) -> Response:
    return Response({'detail': str(exc)}, status=exc.code)


def _no_start() -> Response:
    return Response({'detail': 'Choisissez un créneau.'}, status=400)


def _rules() -> dict:
    config = agenda.settings()
    return {'visit_duration_min': config.visit_minutes, 'extra_listing_min': config.extra_listing_minutes,
            'max_listings': config.max_listings, 'notice_h': config.notice_hours,
            'horizon_days': config.horizon_days, 'same_site_distance_m': config.same_site_distance_m}


class MyVisitView(APIView):
    permission_classes = [IsHost]

    def get(self, request):
        return Response({'listings': appointments.listings_to_schedule(request.user), 'rules': _rules()})


class FreeSlotsView(APIView):
    permission_classes = [IsHost]

    def get(self, request):
        try:
            slots = appointments.free_slots(request.user, _ids(request.query_params.get('listings')))
        except appointments.AppointmentError as exc:
            return _refused(exc)
        return Response({'slots': slots})


class BookView(APIView):
    permission_classes = [IsHost]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'agenda_booking'

    def post(self, request):
        start = _start(request.data.get('start'))
        if start is None:
            return _no_start()
        try:
            appointment = appointments.book(request.user, _ids(request.data.get('listings')), start)
        except appointments.AppointmentError as exc:
            return _refused(exc)
        activity.record('visit_booked', request, actor=request.user, appointment=str(appointment.id),
                        title=appointment.title)
        return Response(appointments.host_appointment_json(appointment), status=201)


class MoveSlotsView(APIView):
    permission_classes = [IsHost]

    def get(self, request, pk):
        try:
            slots = appointments.free_slots_to_move(request.user, pk)
        except appointments.AppointmentError as exc:
            return _refused(exc)
        return Response({'slots': slots})


class MoveView(APIView):
    permission_classes = [IsHost]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'agenda_booking'

    def post(self, request, pk):
        start = _start(request.data.get('start'))
        if start is None:
            return _no_start()
        try:
            appointment = appointments.move(request.user, pk, start)
        except appointments.AppointmentError as exc:
            return _refused(exc)
        activity.record('visit_moved', request, actor=request.user, appointment=str(appointment.id),
                        title=appointment.title)
        return Response(appointments.host_appointment_json(appointment))


class BookByPhoneView(APIView):
    permission_classes = [EstVerificateur]

    def post(self, request, pk):
        start = _start(request.data.get('start'))
        if start is None:
            return Response({'detail': "Indiquez la date et l'heure convenues."}, status=400)
        listing_ids = [str(pk)] + [i for i in _ids(request.data.get('listings')) if i != str(pk)]
        try:
            appointment = appointments.book_by_phone(request.user, listing_ids, start)
        except appointments.AppointmentError as exc:
            return _refused(exc)
        activity.record('visit_booked_by_phone', request, actor=request.user, appointment=str(appointment.id),
                        title=appointment.title)
        return Response(agenda.summary(appointment), status=201)


class CancelView(APIView):
    permission_classes = [EstVerificateur]

    def post(self, request, pk):
        try:
            appointment = appointments.cancel(request.user, pk, str(request.data.get('reason', '')))
        except appointments.AppointmentError as exc:
            return _refused(exc)
        activity.record('visit_cancelled', request, actor=request.user, appointment=str(appointment.id),
                        title=appointment.title)
        return Response(agenda.summary(appointment))


class PostCheckView(APIView):
    permission_classes = [EstVerificateur]

    def post(self, request, pk):
        compliant = request.data.get('compliant')
        if not isinstance(compliant, bool):
            return Response({'compliant': ['Valeur booléenne attendue.']}, status=400)
        try:
            appointment = appointments.post_check(request.user, pk, compliant, str(request.data.get('reason', '')))
        except appointments.AppointmentError as exc:
            return _refused(exc)
        activity.record('visit_post_check', request, actor=request.user, appointment=str(appointment.id),
                        title=appointment.title,
                        compliant=compliant)
        return Response(agenda.summary(appointment))


class ReassignView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            appointment = appointments.reassign(request.user, pk, request.data.get('agent_id'))
        except appointments.AppointmentError as exc:
            return _refused(exc)
        activity.record('visit_reassigned', request, actor=request.user, appointment=str(appointment.id),
                        title=appointment.title,
                        agent=str(appointment.agent_id))
        return Response(agenda.summary(appointment))
