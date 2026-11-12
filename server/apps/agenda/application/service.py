import logging
import statistics
import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta
from typing import Callable

from apps.agenda.domain import rules as r
from apps.agenda.domain.entities import (
    BLOCK, CANCELLED, CONFIRMED, DONE, EXTRA, ORIGIN_HOST, ORIGIN_PHONE, Agenda, Appointment, AvailabilityException,
    Target, WeeklySlot,
)
from apps.agenda.domain.exceptions import (
    ActionNotAllowed, AlreadyBooked, AppointmentNotFound, DailyLimitReached, InvalidRule, SlotUnavailable,
)

from .ports import (
    AgendaRepository, AppointmentRepository, Clock, DigestRepository, Notifier, PeopleLookup, TransactionManager,
)

logger = logging.getLogger('apps.agenda')

BY_AGENT, BY_ADMIN, BY_HOST = 'agent', 'admin', 'host'


@dataclass(frozen=True)
class BookingRequest:
    requester_id: uuid.UUID
    city: str
    targets: list[Target]
    start: datetime
    address: str = ''
    agent_id: uuid.UUID | None = None
    waiting_since: datetime | None = None


@dataclass(frozen=True)
class Settings:
    digest_hour: int = 18
    decision_delay: timedelta = timedelta(hours=2)
    availability_reminder_every: timedelta = timedelta(days=7)
    on_the_way_window: timedelta = timedelta(hours=3)


class AgendaService:
    def __init__(self, *, agendas: AgendaRepository, appointments: AppointmentRepository, digests: DigestRepository,
                 people: PeopleLookup, notifier: Notifier, tx: TransactionManager, clock: Clock, rules: r.Rules,
                 settings: Settings, tasks: Callable[[], list[Callable[[], dict | None]]]):
        self.agendas = agendas
        self.appointments = appointments
        self.digests = digests
        self.people = people
        self.notifier = notifier
        self.tx = tx
        self.clock = clock
        self.rules = rules
        self.settings = settings
        self.tasks = tasks

    def agenda(self, agent_id: uuid.UUID) -> Agenda:
        return self.agendas.for_agent(agent_id) or self.agendas.create(agent_id)

    def set_week(self, agent_id: uuid.UUID, cities: list[str], slots: list[WeeklySlot]) -> Agenda:
        r.check_weekly_slots(slots)
        clean = []
        for city in cities:
            city = ' '.join(city.split())
            if city and r.normalize_city(city) not in {r.normalize_city(c) for c in clean}:
                clean.append(city[:100])
        with self.tx.atomic():
            self.agendas.save_week(self.agenda(agent_id), clean, slots)
        return self.agenda(agent_id)

    def add_exception(self, agent_id: uuid.UUID, exception: AvailabilityException) -> AvailabilityException:
        if exception.kind not in (BLOCK, EXTRA):
            raise InvalidRule("Type d'exception inconnu.")
        if (exception.start is None) != (exception.end is None):
            raise InvalidRule("Indiquez le début et la fin, ou aucun des deux pour la journée entière.")
        if exception.kind == EXTRA and exception.start is None:
            raise InvalidRule("Un ajout ponctuel a une heure de début et de fin.")
        if exception.start is not None and exception.start >= exception.end:
            raise InvalidRule("La fin doit être après le début.")
        agenda = self.agenda(agent_id)
        if exception.day < r.local_day(agenda, self.clock.now()):
            raise InvalidRule("Cette date est passée.")
        return self.agendas.add_exception(agenda, exception)

    def delete_exception(self, agent_id: uuid.UUID, exception_id: int) -> None:
        if not self.agendas.delete_exception(self.agenda(agent_id), exception_id):
            raise AppointmentNotFound("Exception introuvable.")

    def set_day_limit(self, agent_id: uuid.UUID, day: date, max_visits: int | None) -> Agenda:
        if max_visits is not None and not 1 <= max_visits <= self.rules.per_day_ceiling:
            raise InvalidRule(f"Entre 1 et {self.rules.per_day_ceiling} visites par jour.")
        agenda = self.agenda(agent_id)
        if day < r.local_day(agenda, self.clock.now()):
            raise InvalidRule("Cette date est passée.")
        self.agendas.set_day_limit(agenda, day, None if max_visits == self.rules.max_per_day else max_visits)
        return self.agenda(agent_id)

    def _active_agents(self, agent_ids) -> set[uuid.UUID]:
        return {pid for pid, p in self.people.people(agent_ids).items() if p.active_agent}

    def _candidates(self, city: str, agent_id: uuid.UUID | None) -> list[Agenda]:
        if agent_id is not None:
            agenda = self.agendas.for_agent(agent_id)
            return [agenda] if agenda else []
        covering = [a for a in self.agendas.all() if r.covers(a, city)]
        active = self._active_agents(a.agent_id for a in covering)
        return [a for a in covering if a.agent_id in active]

    def _window(self, *moments: datetime) -> tuple[datetime, datetime]:
        now = self.clock.now()
        return (min([now, *moments]) - timedelta(days=1),
                max([now + self.rules.horizon, *moments]) + timedelta(days=1))

    def _with_appointments(self, agendas: list[Agenda], *moments: datetime) -> list[tuple[Agenda, list[Appointment]]]:
        start, end = self._window(*moments)
        found = self.appointments.active_for_agendas([a.id for a in agendas], start, end)
        return [(a, [x for x in found if x.agenda_id == a.id]) for a in agendas]

    def free_slots(self, city: str, listing_count: int, agent_id: uuid.UUID | None = None,
                   exclude: uuid.UUID | None = None) -> list[datetime]:
        length = r.duration(listing_count, self.rules)
        now = self.clock.now()
        found = set()
        for agenda, appointments in self._with_appointments(self._candidates(city, agent_id)):
            found.update(r.free_slots(agenda, appointments, length, now=now, rules=self.rules, exclude=exclude))
        return sorted(found)

    def _lock(self, agendas: list[Agenda]) -> list[Agenda]:
        self.agendas.lock(sorted(a.id for a in agendas))
        return [self.agendas.for_agent(a.agent_id) for a in agendas]

    def _new(self, agenda: Agenda, request: BookingRequest, length: timedelta, origin: str) -> Appointment:
        return Appointment(
            agenda_id=agenda.id, agent_id=agenda.agent_id, requester_id=request.requester_id,
            targets=list(request.targets), city=request.city, address=request.address, start=request.start,
            end=request.start + length, blocked_until=request.start + length + self.rules.margin,
            origin=origin, waiting_since=request.waiting_since, created_at=self.clock.now(),
        )

    def _check_targets_free(self, targets: list[Target]) -> None:
        ids = [t.id for t in targets]
        self.appointments.lock_targets(ids)
        if self.appointments.confirmed_for_targets(ids):
            raise AlreadyBooked("Une visite est déjà prévue pour cette annonce.")

    def book(self, request: BookingRequest) -> Appointment:
        length = r.duration(len(request.targets), self.rules)
        r.check_same_site(request.targets, self.rules)
        now = self.clock.now()
        with self.tx.atomic():
            self._check_targets_free(request.targets)
            candidates = self._candidates(request.city, request.agent_id)
            if not candidates:
                raise SlotUnavailable("Aucun agent ne propose de visite dans cette ville pour le moment.")
            possible, error = [], None
            for agenda, appointments in self._with_appointments(self._lock(candidates), request.start):
                try:
                    r.check(agenda, appointments, request.start, length, now=now, rules=self.rules)
                    possible.append((agenda, appointments))
                except (SlotUnavailable, DailyLimitReached) as exc:
                    error = exc
            if not possible:
                if isinstance(error, SlotUnavailable):
                    raise error
                raise SlotUnavailable("Ce créneau n'est plus disponible : choisissez-en un autre.")
            agenda = r.choose(possible, request.start)
            appointment = self.appointments.add(self._new(agenda, request, length, ORIGIN_HOST))
            self.notifier.confirmed(appointment, agenda)
        return appointment

    def book_by_phone(self, agent_id: uuid.UUID, request: BookingRequest) -> Appointment:
        length = r.duration(len(request.targets), self.rules)
        r.check_same_site(request.targets, self.rules)
        now = self.clock.now()
        if request.start <= now:
            raise InvalidRule("Choisissez une date à venir.")
        with self.tx.atomic():
            self._check_targets_free(request.targets)
            agenda, = self._lock([self.agenda(agent_id)])
            (agenda, appointments), = self._with_appointments([agenda], request.start)
            r.check(agenda, appointments, request.start, length, now=now, rules=self.rules, check_availability=False)
            appointment = self.appointments.add(self._new(agenda, request, length, ORIGIN_PHONE))
            self.notifier.confirmed(appointment, agenda)
        return appointment

    def get(self, appointment_id: uuid.UUID) -> Appointment:
        appointment = self.appointments.get(appointment_id)
        if appointment is None:
            raise AppointmentNotFound("Rendez-vous introuvable.")
        return appointment

    def _confirmed(self, appointment_id: uuid.UUID) -> Appointment:
        appointment = self.get(appointment_id)
        if appointment.status != CONFIRMED:
            raise ActionNotAllowed("Ce rendez-vous n'est plus prévu.")
        return appointment

    def move(self, appointment_id: uuid.UUID, requester_id: uuid.UUID, start: datetime) -> Appointment:
        now = self.clock.now()
        with self.tx.atomic():
            appointment = self._confirmed(appointment_id)
            if appointment.requester_id != requester_id:
                raise AppointmentNotFound("Rendez-vous introuvable.")
            if appointment.start - self.rules.notice < now:
                raise ActionNotAllowed("Un rendez-vous se déplace jusqu'à 24 h avant la visite.")
            agenda, = self._lock([self.agendas.for_agent(appointment.agent_id)])
            (agenda, appointments), = self._with_appointments([agenda], start)
            length = appointment.end - appointment.start
            r.check(agenda, appointments, start, length, now=now, rules=self.rules, exclude=appointment.id)
            appointment = self.appointments.save(replace(
                appointment, start=start, end=start + length, blocked_until=start + length + self.rules.margin,
                sequence=appointment.sequence + 1, host_reminder_at=None, on_the_way_at=None))
            self.notifier.moved(appointment, agenda)
        return appointment

    def cancel(self, appointment_id: uuid.UUID, *, author_id: uuid.UUID, by: str, reason: str) -> Appointment:
        reason = ' '.join(reason.split())
        if by not in (BY_AGENT, BY_ADMIN, BY_HOST):
            raise InvalidRule("Auteur de l'annulation inconnu.")
        if by != BY_HOST and len(reason) < 5:
            raise InvalidRule("Expliquez à l'hôte pourquoi la visite est annulée (5 caractères au moins).")
        with self.tx.atomic():
            appointment = self._confirmed(appointment_id)
            if by == BY_AGENT and appointment.agent_id != author_id:
                raise ActionNotAllowed("Seul l'agent de cette visite ou un administrateur peut l'annuler.")
            if by == BY_HOST and appointment.requester_id != author_id:
                raise AppointmentNotFound("Rendez-vous introuvable.")
            appointment = self.appointments.save(replace(
                appointment, status=CANCELLED, cancelled_at=self.clock.now(), cancelled_by=by,
                cancellation_reason=reason[:500], sequence=appointment.sequence + 1))
            self.notifier.cancelled(appointment, self.agendas.for_agent(appointment.agent_id))
        return appointment

    def reassign(self, appointment_id: uuid.UUID, agent_id: uuid.UUID) -> Appointment:
        now = self.clock.now()
        with self.tx.atomic():
            appointment = self._confirmed(appointment_id)
            if appointment.agent_id == agent_id:
                return appointment
            if agent_id not in self._active_agents([agent_id]):
                raise InvalidRule("Cet agent n'est pas actif.")
            current, target = self.agendas.for_agent(appointment.agent_id), self.agenda(agent_id)
            locked = {a.agent_id: a for a in self._lock([current, target])}
            (target, appointments), = self._with_appointments([locked[agent_id]], appointment.start)
            r.check(target, appointments, appointment.start, appointment.end - appointment.start, now=now,
                    rules=self.rules, check_availability=False)
            previous_agent_id = appointment.agent_id
            appointment = self.appointments.save(replace(
                appointment, agenda_id=target.id, agent_id=agent_id, sequence=appointment.sequence + 1,
                on_the_way_at=None))
            self.notifier.reassigned(appointment, target, previous_agent_id)
        return appointment

    def on_the_way(self, appointment_id: uuid.UUID, agent_id: uuid.UUID) -> Appointment:
        now = self.clock.now()
        with self.tx.atomic():
            appointment = self._confirmed(appointment_id)
            if appointment.agent_id != agent_id:
                raise ActionNotAllowed("Ce rendez-vous est celui d'un autre agent.")
            if not appointment.start - self.settings.on_the_way_window <= now <= appointment.end:
                raise ActionNotAllowed("« Je suis en route » s'envoie le jour de la visite, peu avant l'heure.")
            if appointment.on_the_way_at:
                return appointment
            appointment = self.appointments.save(replace(appointment, on_the_way_at=now))
            self.notifier.on_the_way(appointment, self.agendas.for_agent(agent_id))
        return appointment

    def mark_done(self, target_id: str) -> None:
        now = self.clock.now()
        for appointment in self.appointments.confirmed_for_targets([str(target_id)]):
            self.appointments.save(replace(appointment, status=DONE, done_at=now))

    def confirmed_for_targets(self, target_ids) -> list[Appointment]:
        return self.appointments.confirmed_for_targets([str(i) for i in target_ids])

    def between(self, start: datetime, end: datetime, agent_id: uuid.UUID | None = None) -> list[Appointment]:
        return self.appointments.between(start, end, agent_id, with_cancelled=True)

    def feed(self, token: str) -> tuple[Agenda, list[Appointment]] | None:
        agenda = self.agendas.for_token(token) if token else None
        if agenda is None or agenda.agent_id not in self._active_agents([agenda.agent_id]):
            return None
        return agenda, self.appointments.feed(agenda.id, self.clock.now() - timedelta(days=30))

    def regenerate_token(self, agent_id: uuid.UUID) -> str:
        return self.agendas.regenerate_token(self.agenda(agent_id))

    def coverage(self) -> list[dict]:
        agendas = self.agendas.all()
        active = self._active_agents(a.agent_id for a in agendas)
        agendas = [a for a in agendas if a.agent_id in active]
        cities: dict[str, str] = {}
        for agenda in agendas:
            for city in agenda.cities:
                cities.setdefault(r.normalize_city(city), city)
        now = self.clock.now()
        length = r.duration(1, self.rules)
        with_appointments = self._with_appointments(agendas)
        result = []
        for _, city in sorted(cities.items()):
            covering = [(a, appointments) for a, appointments in with_appointments if r.covers(a, city)]
            free = set()
            for agenda, appointments in covering:
                free.update(r.free_slots(agenda, appointments, length, now=now, rules=self.rules))
            result.append({
                'city': city, 'agent_ids': [str(a.agent_id) for a, _ in covering], 'free_slots': len(free),
                'upcoming_visits': sum(1 for _, appointments in covering for x in appointments
                                       if x.status == CONFIRMED and x.start >= now),
            })
        return result

    def delays(self, days: int = 90) -> dict:
        appointments = self.appointments.created_since(self.clock.now() - timedelta(days=days))

        def hours(pairs) -> dict:
            values = [(b - a).total_seconds() / 3600 for a, b in pairs if a and b]
            return {'count': len(values), 'median_h': round(statistics.median(values), 1) if values else None,
                    'mean_h': round(statistics.fmean(values), 1) if values else None}

        return {
            'days': days,
            'listing_to_booking': hours((x.waiting_since, x.created_at) for x in appointments),
            'booking_to_visit': hours((x.created_at, x.start) for x in appointments),
            'visit_to_decision': hours((x.start, x.done_at) for x in appointments if x.status == DONE),
            'by_phone': sum(1 for x in appointments if x.origin == ORIGIN_PHONE),
            'total': len(appointments),
        }

    def _day_bounds(self, agenda: Agenda, day: date) -> tuple[datetime, datetime]:
        start = datetime.combine(day, time.min, tzinfo=agenda.tz)
        return start, start + timedelta(days=1)

    def _evening_before(self, now: datetime) -> dict:
        digests = reminders = 0
        for agenda in self.agendas.all():
            local = now.astimezone(agenda.tz)
            if local.hour < self.settings.digest_hour:
                continue
            tomorrow = local.date() + timedelta(days=1)
            appointments = [x for x in self.appointments.between(*self._day_bounds(agenda, tomorrow), agenda.agent_id)
                            if x.status == CONFIRMED]
            for appointment in appointments:
                if appointment.host_reminder_at is None:
                    with self.tx.atomic():
                        self.appointments.save(replace(appointment, host_reminder_at=now))
                        self.notifier.host_reminder(appointment, agenda)
                    reminders += 1
            if appointments:
                with self.tx.atomic():
                    if self.digests.mark(agenda.id, tomorrow, now):
                        self.notifier.agent_digest(agenda, tomorrow, sorted(appointments, key=lambda x: x.start))
                        digests += 1
        return {'digests': digests, 'host_reminders': reminders}

    def _availability_reminders(self, now: datetime) -> int:
        sent = 0
        for agent_id in self.people.active_agents():
            agenda = self.agenda(agent_id)
            if r.has_availability(agenda, now, self.rules):
                continue
            last = agenda.availability_reminder_at
            if last and last > now - self.settings.availability_reminder_every:
                continue
            with self.tx.atomic():
                self.agendas.mark_availability_reminder(agenda, now)
                self.notifier.availability_reminder(agent_id)
            sent += 1
        return sent

    def _without_decision(self, now: datetime) -> int:
        appointments = self.appointments.without_decision(now - self.settings.decision_delay)
        if appointments:
            with self.tx.atomic():
                for appointment in appointments:
                    self.appointments.save(replace(appointment, alert_at=now))
                self.notifier.visits_without_decision(appointments)
        return len(appointments)

    def run(self) -> dict:
        now = self.clock.now()
        stats = {**self._evening_before(now), 'availability_reminders': self._availability_reminders(now),
                 'without_decision': self._without_decision(now)}
        for task in self.tasks():
            try:
                result = task()
                if result:
                    stats.update(result)
            except Exception:
                logger.exception("Agenda periodic task failed: %s", getattr(task, '__name__', task))
        return {k: v for k, v in stats.items() if v}
