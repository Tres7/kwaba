import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import ContextManager

from apps.agenda.domain.entities import Agenda, Appointment, AvailabilityException, WeeklySlot


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        pass


class TransactionManager(ABC):
    @abstractmethod
    def atomic(self) -> ContextManager:
        pass


class AgendaRepository(ABC):
    @abstractmethod
    def for_agent(self, agent_id: uuid.UUID) -> Agenda | None:
        pass

    @abstractmethod
    def create(self, agent_id: uuid.UUID) -> Agenda:
        pass

    @abstractmethod
    def lock(self, agenda_ids: list[uuid.UUID]) -> None:
        pass

    @abstractmethod
    def all(self) -> list[Agenda]:
        pass

    @abstractmethod
    def for_token(self, token: str) -> Agenda | None:
        pass

    @abstractmethod
    def save_week(self, agenda: Agenda, cities: list[str], slots: list[WeeklySlot]) -> None:
        pass

    @abstractmethod
    def add_exception(self, agenda: Agenda, exception: AvailabilityException) -> AvailabilityException:
        pass

    @abstractmethod
    def delete_exception(self, agenda: Agenda, exception_id: int) -> bool:
        pass

    @abstractmethod
    def set_day_limit(self, agenda: Agenda, day: date, max_visits: int | None) -> None:
        pass

    @abstractmethod
    def regenerate_token(self, agenda: Agenda) -> str:
        pass

    @abstractmethod
    def mark_availability_reminder(self, agenda: Agenda, moment: datetime) -> None:
        pass


class AppointmentRepository(ABC):
    @abstractmethod
    def add(self, appointment: Appointment) -> Appointment:
        pass

    @abstractmethod
    def save(self, appointment: Appointment) -> Appointment:
        pass

    @abstractmethod
    def get(self, appointment_id: uuid.UUID) -> Appointment | None:
        pass

    @abstractmethod
    def active_for_agendas(self, agenda_ids: list[uuid.UUID], start: datetime, end: datetime) -> list[Appointment]:
        pass

    @abstractmethod
    def between(self, start: datetime, end: datetime, agent_id: uuid.UUID | None = None,
                with_cancelled: bool = False) -> list[Appointment]:
        pass

    @abstractmethod
    def lock_targets(self, target_ids: list[str]) -> None:
        pass

    @abstractmethod
    def confirmed_for_targets(self, target_ids: list[str]) -> list[Appointment]:
        pass

    @abstractmethod
    def feed(self, agenda_id: uuid.UUID, since: datetime) -> list[Appointment]:
        pass

    @abstractmethod
    def without_decision(self, before: datetime) -> list[Appointment]:
        pass

    @abstractmethod
    def created_since(self, since: datetime) -> list[Appointment]:
        pass


class DigestRepository(ABC):
    @abstractmethod
    def mark(self, agenda_id: uuid.UUID, day: date, moment: datetime) -> bool:
        pass


@dataclass(frozen=True)
class Person:
    id: uuid.UUID
    name: str
    email: str
    active_agent: bool = True


class PeopleLookup(ABC):
    @abstractmethod
    def person(self, user_id: uuid.UUID) -> Person | None:
        pass

    @abstractmethod
    def people(self, user_ids) -> dict[uuid.UUID, Person]:
        pass

    @abstractmethod
    def active_agents(self) -> list[uuid.UUID]:
        pass

    @abstractmethod
    def admin_emails(self) -> list[str]:
        pass


class Notifier(ABC):
    @abstractmethod
    def confirmed(self, appointment: Appointment, agenda: Agenda) -> None:
        pass

    @abstractmethod
    def moved(self, appointment: Appointment, agenda: Agenda) -> None:
        pass

    @abstractmethod
    def cancelled(self, appointment: Appointment, agenda: Agenda) -> None:
        pass

    @abstractmethod
    def reassigned(self, appointment: Appointment, agenda: Agenda, previous_agent_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    def host_reminder(self, appointment: Appointment, agenda: Agenda) -> None:
        pass

    @abstractmethod
    def on_the_way(self, appointment: Appointment, agenda: Agenda) -> None:
        pass

    @abstractmethod
    def agent_digest(self, agenda: Agenda, day: date, appointments: list[Appointment]) -> None:
        pass

    @abstractmethod
    def availability_reminder(self, agent_id: uuid.UUID) -> None:
        pass

    @abstractmethod
    def visits_without_decision(self, appointments: list[Appointment]) -> None:
        pass
