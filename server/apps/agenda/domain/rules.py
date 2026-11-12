import math
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .entities import BLOCK, EXTRA, Agenda, Appointment, Target, WeeklySlot
from .exceptions import DailyLimitReached, InvalidRule, SlotUnavailable


@dataclass(frozen=True)
class Rules:
    visit_duration: timedelta = timedelta(minutes=60)
    extra_listing: timedelta = timedelta(minutes=20)
    max_listings: int = 5
    margin: timedelta = timedelta(minutes=30)
    max_per_day: int = 4
    per_day_ceiling: int = 10
    notice: timedelta = timedelta(hours=24)
    horizon: timedelta = timedelta(days=14)
    step: timedelta = timedelta(minutes=30)
    same_site_distance_m: int = 200


def normalize_city(city: str) -> str:
    without_accents = ''.join(c for c in unicodedata.normalize('NFKD', city) if not unicodedata.combining(c))
    return ' '.join(without_accents.casefold().replace('-', ' ').split())


def covers(agenda: Agenda, city: str) -> bool:
    wanted = normalize_city(city)
    return bool(wanted) and any(normalize_city(c) == wanted for c in agenda.cities)


def duration(listing_count: int, rules: Rules) -> timedelta:
    if listing_count < 1:
        raise InvalidRule("Choisissez au moins une annonce.")
    if listing_count > rules.max_listings:
        raise InvalidRule(f"Une visite groupée compte {rules.max_listings} annonces au plus.")
    return rules.visit_duration + (listing_count - 1) * rules.extra_listing


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def check_same_site(targets: list[Target], rules: Rules) -> None:
    if len(targets) <= 1:
        return
    if len({t.id for t in targets}) != len(targets):
        raise InvalidRule("Une annonce apparaît deux fois.")
    if any(t.latitude is None or t.longitude is None for t in targets):
        raise InvalidRule("Chaque annonce d'une visite groupée doit avoir sa position sur la carte.")
    positions = [(float(t.latitude), float(t.longitude)) for t in targets]
    for i, a in enumerate(positions):
        for b in positions[i + 1:]:
            if distance_m(a, b) > rules.same_site_distance_m:
                raise InvalidRule(
                    f"Ces annonces ne sont pas sur le même site (plus de {rules.same_site_distance_m} m) : "
                    "réservez une visite pour chacune.")


def check_weekly_slots(slots: list[WeeklySlot]) -> None:
    for slot in slots:
        if not 0 <= slot.weekday <= 6:
            raise InvalidRule("Jour de la semaine inconnu.")
        if slot.start >= slot.end:
            raise InvalidRule("Une plage doit finir après son début.")


def _subtract(intervals, start, end):
    result = []
    for a, b in intervals:
        if end <= a or b <= start:
            result.append((a, b))
            continue
        if a < start:
            result.append((a, start))
        if end < b:
            result.append((end, b))
    return result


def _merge(intervals):
    merged = []
    for a, b in sorted(intervals):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def day_windows(agenda: Agenda, day: date) -> list[tuple[datetime, datetime]]:
    tz = agenda.tz

    def at(hour: time) -> datetime:
        return datetime.combine(day, hour, tzinfo=tz)

    intervals = [(at(s.start), at(s.end)) for s in agenda.weekly_slots if s.weekday == day.weekday()]
    of_the_day = [e for e in agenda.exceptions if e.day == day]
    for e in of_the_day:
        if e.kind != BLOCK:
            continue
        if e.start is None or e.end is None:
            intervals = []
        else:
            intervals = _subtract(intervals, at(e.start), at(e.end))
    intervals += [(at(e.start), at(e.end)) for e in of_the_day
                  if e.kind == EXTRA and e.start is not None and e.end is not None]
    return _merge(intervals)


def local_day(agenda: Agenda, moment: datetime) -> date:
    return moment.astimezone(agenda.tz).date()


def day_limit(agenda: Agenda, day: date, rules: Rules) -> int:
    return agenda.day_limits.get(day, rules.max_per_day)


def visits_on_day(agenda: Agenda, appointments: list[Appointment], day: date, exclude=None) -> int:
    return sum(1 for a in appointments if a.active and a.id != exclude and local_day(agenda, a.start) == day)


def _overlaps(a0, a1, b0, b1) -> bool:
    return a0 < b1 and b0 < a1


def _check_occupancy(agenda, appointments, start, length, rules, exclude) -> None:
    blocked_until = start + length + rules.margin
    for a in appointments:
        if a.active and a.id != exclude and _overlaps(start, blocked_until, a.start, a.blocked_until):
            raise SlotUnavailable("Ce créneau vient d'être pris : choisissez-en un autre.")
    day = local_day(agenda, start)
    if visits_on_day(agenda, appointments, day, exclude) >= day_limit(agenda, day, rules):
        raise DailyLimitReached("La limite de visites de cette journée est atteinte.")


def fits_windows(agenda: Agenda, start: datetime, length: timedelta) -> bool:
    end = start + length
    return any(a <= start and end <= b for a, b in day_windows(agenda, local_day(agenda, start)))


def check(agenda: Agenda, appointments: list[Appointment], start: datetime, length: timedelta, *, now: datetime,
          rules: Rules, check_availability: bool = True, exclude=None) -> None:
    if check_availability:
        if start < now + rules.notice:
            raise SlotUnavailable("Une visite se réserve au moins 24 h à l'avance.")
        if start > now + rules.horizon:
            raise SlotUnavailable("Une visite se réserve dans les 14 prochains jours.")
        if not fits_windows(agenda, start, length):
            raise SlotUnavailable("Ce créneau n'est plus disponible : choisissez-en un autre.")
    _check_occupancy(agenda, appointments, start, length, rules, exclude)


def free_slots(agenda: Agenda, appointments: list[Appointment], length: timedelta, *, now: datetime, rules: Rules,
               exclude=None) -> list[datetime]:
    first, last = now + rules.notice, now + rules.horizon
    day, last_day = local_day(agenda, first), local_day(agenda, last)
    found = []
    while day <= last_day:
        for a, b in day_windows(agenda, day):
            moment = a
            while moment + length <= b:
                if first <= moment <= last:
                    try:
                        _check_occupancy(agenda, appointments, moment, length, rules, exclude)
                        found.append(moment)
                    except (SlotUnavailable, DailyLimitReached):
                        pass
                moment += rules.step
        day += timedelta(days=1)
    return found


def has_availability(agenda: Agenda, now: datetime, rules: Rules) -> bool:
    day = local_day(agenda, now)
    for i in range(rules.horizon.days + 1):
        if any(b > now for _, b in day_windows(agenda, day + timedelta(days=i))):
            return True
    return False


def choose(candidates: list[tuple[Agenda, list[Appointment]]], start: datetime) -> Agenda:
    def key(candidate):
        agenda, appointments = candidate
        return (visits_on_day(agenda, appointments, local_day(agenda, start)),
                sum(1 for a in appointments if a.active), str(agenda.agent_id))

    return min(candidates, key=key)[0]
