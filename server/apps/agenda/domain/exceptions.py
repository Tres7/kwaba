class AgendaError(Exception):
    code = 400


class InvalidRule(AgendaError):
    pass


class SlotUnavailable(AgendaError):
    code = 409


class DailyLimitReached(AgendaError):
    code = 409


class AlreadyBooked(AgendaError):
    code = 409


class AppointmentNotFound(AgendaError):
    code = 404


class ActionNotAllowed(AgendaError):
    code = 403
