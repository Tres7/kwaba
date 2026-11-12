from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

from apps.export import api as export


def _unfold(content: str) -> list[str]:
    return content.replace('\r\n ', '').split('\r\n')


def _event(**fields):
    values = {
        'uid': 'visit-1@kwa-ba.com',
        'start': datetime(2026, 11, 20, 9, 0, tzinfo=dt_timezone.utc),
        'end': datetime(2026, 11, 20, 10, 0, tzinfo=dt_timezone.utc),
        'title': 'Visite · Villa, vue mer',
    }
    return export.Event(**{**values, **fields})


def test_escapes_special_characters():
    assert export.escape('a,b;c\\d\ne') == 'a\\,b\\;c\\\\d\\ne'
    assert export.escape('a\r\nb\rc') == 'a\\nb\\nc'


def test_folds_lines_without_splitting_a_character():
    lines = export.fold('DESCRIPTION:' + 'é' * 60).split('\r\n')
    assert [len(line.encode('utf-8')) for line in lines] == [74, 59]
    assert all(line.startswith(' ') for line in lines[1:])


def test_dates_are_written_in_utc():
    lome = datetime(2026, 11, 20, 9, 30, tzinfo=ZoneInfo('Africa/Lome'))
    paris = datetime(2026, 7, 20, 11, 30, tzinfo=ZoneInfo('Europe/Paris'))
    assert export.utc_stamp(lome) == '20261120T093000Z'
    assert export.utc_stamp(paris) == '20260720T093000Z'
    assert export.utc_stamp(datetime(2026, 11, 20, 9, 30)) == '20261120T093000Z'


def test_calendar_with_one_event_and_an_alarm():
    content = export.calendar([_event(alarm='-P1D', alarm_text='Demain')], prodid='-//Kwa-Ba//Test//FR')
    lines = _unfold(content)
    assert lines[0] == 'BEGIN:VCALENDAR' and lines[-2] == 'END:VCALENDAR' and content.endswith('\r\n')
    assert 'PRODID:-//Kwa-Ba//Test//FR' in lines
    assert 'DTSTART:20261120T090000Z' in lines and 'DTEND:20261120T100000Z' in lines
    assert 'SUMMARY:Visite · Villa\\, vue mer' in lines
    assert 'STATUS:CONFIRMED' in lines
    assert 'TRIGGER:-P1D' in lines and 'DESCRIPTION:Demain' in lines
    assert all(len(line.encode('utf-8')) <= 75 for line in content.split('\r\n'))


def test_optional_fields_are_left_out():
    lines = _unfold(export.calendar([_event()], prodid='-//x//y//FR'))
    assert not any(line.startswith(('LOCATION:', 'DESCRIPTION:', 'URL:', 'SEQUENCE:', 'BEGIN:VALARM'))
                   for line in lines)


def test_cancelled_event_keeps_its_uid_with_a_sequence():
    lines = _unfold(export.calendar([_event(status='CANCELLED', sequence=2)], prodid='-//x//y//FR', name='Agenda'))
    assert 'UID:visit-1@kwa-ba.com' in lines
    assert 'STATUS:CANCELLED' in lines and 'SEQUENCE:2' in lines
    assert 'X-WR-CALNAME:Agenda' in lines


def test_several_events():
    content = export.calendar([_event(), _event(uid='visit-2@kwa-ba.com')], prodid='-//x//y//FR')
    assert content.count('BEGIN:VEVENT') == 2


def test_response_headers():
    response = export.ics_response('BEGIN:VCALENDAR\r\n', 'agenda.ics')
    assert response['Content-Type'] == 'text/calendar; charset=utf-8'
    assert response['Content-Disposition'] == 'attachment; filename="agenda.ics"'
    assert response['Cache-Control'] == 'private, no-store'
    assert export.ics_response('', 'feed.ics', attachment=False)['Content-Disposition'] == 'inline; filename="feed.ics"'
