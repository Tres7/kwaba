import secrets
import uuid

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.db.models import F, Func, Q


def new_token() -> str:
    return secrets.token_urlsafe(32)


class TsTzRange(Func):
    function = 'TSTZRANGE'
    output_field = DateTimeRangeField()


class AgendaModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_id = models.UUIDField(unique=True)
    timezone = models.CharField(max_length=64, default='Africa/Lome')
    cities = models.JSONField(default=list, blank=True)
    ics_token = models.CharField(max_length=64, unique=True, default=new_token)
    availability_reminder_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'agenda_agenda'
        verbose_name = "Agenda d'agent"
        verbose_name_plural = 'Agendas des agents'

    def __str__(self):
        return f"Agenda {self.agent_id}"


class WeeklySlotModel(models.Model):
    agenda = models.ForeignKey(AgendaModel, on_delete=models.CASCADE, related_name='weekly_slots')
    weekday = models.PositiveSmallIntegerField()
    start = models.TimeField()
    end = models.TimeField()

    class Meta:
        db_table = 'agenda_weekly_slot'
        ordering = ['weekday', 'start']
        constraints = [
            models.CheckConstraint(condition=Q(end__gt=F('start')), name='agenda_weekly_slot_end_after_start'),
            models.CheckConstraint(condition=Q(weekday__lte=6), name='agenda_weekly_slot_valid_weekday'),
        ]


class AvailabilityExceptionModel(models.Model):
    KINDS = [('block', 'Indisponible'), ('extra', 'Disponible en plus')]

    agenda = models.ForeignKey(AgendaModel, on_delete=models.CASCADE, related_name='exceptions')
    day = models.DateField()
    kind = models.CharField(max_length=10, choices=KINDS)
    start = models.TimeField(null=True, blank=True)
    end = models.TimeField(null=True, blank=True)

    class Meta:
        db_table = 'agenda_availability_exception'
        ordering = ['day', 'start']
        indexes = [models.Index(fields=['agenda', 'day'])]


class DayLimitModel(models.Model):
    agenda = models.ForeignKey(AgendaModel, on_delete=models.CASCADE, related_name='day_limits')
    day = models.DateField()
    max_visits = models.PositiveSmallIntegerField()

    class Meta:
        db_table = 'agenda_day_limit'
        constraints = [models.UniqueConstraint(fields=['agenda', 'day'], name='agenda_one_limit_per_day')]


class AppointmentModel(models.Model):
    STATUSES = [('confirmed', 'Confirmé'), ('cancelled', 'Annulé'), ('done', 'Effectué')]
    ORIGINS = [('host', "Réservé par l'hôte"), ('phone', 'Confirmé par téléphone')]
    CANCELLED_BY = [('agent', 'Agent'), ('admin', 'Administrateur'), ('host', 'Hôte')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agenda = models.ForeignKey(AgendaModel, on_delete=models.PROTECT, related_name='appointments')
    agent_id = models.UUIDField(db_index=True)
    requester_id = models.UUIDField(db_index=True)
    targets = models.JSONField(default=list)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255, blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    blocked_until = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUSES, default='confirmed')
    origin = models.CharField(max_length=10, choices=ORIGINS, default='host')
    waiting_since = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    on_the_way_at = models.DateTimeField(null=True, blank=True)
    done_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.CharField(max_length=10, choices=CANCELLED_BY, blank=True)
    cancellation_reason = models.CharField(max_length=500, blank=True)
    closing_reason = models.CharField(max_length=500, blank=True)
    post_check = models.BooleanField(default=False)
    sequence = models.PositiveIntegerField(default=0)
    host_reminder_at = models.DateTimeField(null=True, blank=True)
    alert_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'agenda_appointment'
        ordering = ['start']
        verbose_name = 'Rendez-vous de visite'
        verbose_name_plural = 'Rendez-vous de visite'
        indexes = [models.Index(fields=['status', 'start'])]
        constraints = [
            models.CheckConstraint(condition=Q(end__gt=F('start')) & Q(blocked_until__gte=F('end')),
                                   name='agenda_appointment_ordered_dates'),
            ExclusionConstraint(
                name='agenda_appointment_no_overlap',
                expressions=[
                    ('agenda', RangeOperators.EQUAL),
                    (TsTzRange('start', 'blocked_until'), RangeOperators.OVERLAPS),
                ],
                condition=Q(status='confirmed'),
            ),
        ]

    def __str__(self):
        return f"Visite {self.start:%d/%m/%Y %H:%M} · {self.city}"


class AgendaSettingsModel(models.Model):
    notice_hours = models.PositiveSmallIntegerField(default=24)
    horizon_days = models.PositiveSmallIntegerField(default=14)
    max_per_day = models.PositiveSmallIntegerField(default=4)
    margin_minutes = models.PositiveSmallIntegerField(default=30)
    visit_minutes = models.PositiveSmallIntegerField(default=60)
    extra_listing_minutes = models.PositiveSmallIntegerField(default=20)
    max_listings = models.PositiveSmallIntegerField(default=5)
    same_site_distance_m = models.PositiveSmallIntegerField(default=200)
    digest_hour = models.PositiveSmallIntegerField(default=18)
    decision_alert_hours = models.PositiveSmallIntegerField(default=2)
    host_reminder_days = models.PositiveSmallIntegerField(default=2)
    host_alert_days = models.PositiveSmallIntegerField(default=3)
    updated_at = models.DateTimeField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = 'agenda_settings'
        verbose_name = "Réglages de l'agenda"
        verbose_name_plural = "Réglages de l'agenda"


class DigestModel(models.Model):
    agenda = models.ForeignKey(AgendaModel, on_delete=models.CASCADE, related_name='digests')
    day = models.DateField()
    sent_at = models.DateTimeField()

    class Meta:
        db_table = 'agenda_digest'
        constraints = [models.UniqueConstraint(fields=['agenda', 'day'], name='agenda_one_digest_per_day')]
