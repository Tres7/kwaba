from dataclasses import asdict, dataclass, fields
from datetime import timedelta

from .exceptions import InvalidRule
from .rules import Rules

DEFAULT_TIMEZONE = 'Africa/Lome'
PER_DAY_CEILING = 10
STEP = timedelta(minutes=30)


@dataclass(frozen=True)
class AgendaSettings:
    notice_hours: int = 24
    horizon_days: int = 14
    max_per_day: int = 4
    margin_minutes: int = 30
    visit_minutes: int = 60
    extra_listing_minutes: int = 20
    max_listings: int = 5
    same_site_distance_m: int = 200
    digest_hour: int = 18
    decision_alert_hours: int = 2
    host_reminder_days: int = 2
    host_alert_days: int = 3

    def as_dict(self) -> dict:
        return asdict(self)


BOUNDS: dict[str, tuple[int, int]] = {
    'notice_hours': (1, 72),
    'horizon_days': (7, 60),
    'max_per_day': (1, PER_DAY_CEILING),
    'margin_minutes': (0, 120),
    'visit_minutes': (30, 180),
    'extra_listing_minutes': (0, 60),
    'max_listings': (1, 10),
    'same_site_distance_m': (50, 1000),
    'digest_hour': (12, 22),
    'decision_alert_hours': (1, 48),
    'host_reminder_days': (1, 14),
    'host_alert_days': (1, 14),
}


class InvalidSettings(InvalidRule):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Certains réglages sont hors des limites.")
        self.errors = errors


def validated(current: AgendaSettings, changes: dict) -> AgendaSettings:
    names = {f.name for f in fields(AgendaSettings)}
    values, errors = current.as_dict(), {}
    for name, value in changes.items():
        if name not in names:
            continue
        if not isinstance(value, int) or isinstance(value, bool):
            errors[name] = "Nombre entier attendu."
            continue
        low, high = BOUNDS[name]
        if not low <= value <= high:
            errors[name] = f"Entre {low} et {high}."
            continue
        values[name] = value
    if 'host_alert_days' not in errors and values['host_alert_days'] <= values['host_reminder_days']:
        errors['host_alert_days'] = "L'alerte aux admins doit venir après la relance de l'hôte."
    if errors:
        raise InvalidSettings(errors)
    return AgendaSettings(**values)


def to_rules(settings: AgendaSettings) -> Rules:
    return Rules(
        visit_duration=timedelta(minutes=settings.visit_minutes),
        extra_listing=timedelta(minutes=settings.extra_listing_minutes),
        max_listings=settings.max_listings,
        margin=timedelta(minutes=settings.margin_minutes),
        max_per_day=settings.max_per_day,
        per_day_ceiling=PER_DAY_CEILING,
        notice=timedelta(hours=settings.notice_hours),
        horizon=timedelta(days=settings.horizon_days),
        step=STEP,
        same_site_distance_m=settings.same_site_distance_m,
    )
