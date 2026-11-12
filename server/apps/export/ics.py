from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone

from django.http import HttpResponse
from django.utils import timezone


@dataclass(frozen=True)
class Event:
    uid: str
    start: datetime
    end: datetime
    title: str
    location: str = ''
    description: str = ''
    url: str = ''
    status: str = 'CONFIRMED'
    sequence: int = 0
    alarm: str = ''
    alarm_text: str = ''


def escape(text: str) -> str:
    return (text.replace('\\', '\\\\').replace(';', '\;').replace(',', '\\,')
            .replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n'))


def fold(line: str) -> str:
    chunks, current = [], ''
    for character in line:
        limit = 75 if not chunks else 74
        if len((current + character).encode('utf-8')) > limit:
            chunks.append(current)
            current = character
        else:
            current += character
    chunks.append(current)
    return '\r\n '.join(chunks)


def utc_stamp(moment: datetime) -> str:
    if timezone.is_aware(moment):
        moment = moment.astimezone(dt_timezone.utc)
    return moment.strftime('%Y%m%dT%H%M%SZ')


def _event_lines(event: Event, stamp: str) -> list[str]:
    lines = [
        'BEGIN:VEVENT',
        f'UID:{event.uid}',
        f'DTSTAMP:{stamp}',
        f'DTSTART:{utc_stamp(event.start)}',
        f'DTEND:{utc_stamp(event.end)}',
        f'SUMMARY:{escape(event.title)}',
    ]
    if event.sequence:
        lines.append(f'SEQUENCE:{event.sequence}')
    if event.location:
        lines.append(f'LOCATION:{escape(event.location)}')
    if event.description:
        lines.append(f'DESCRIPTION:{escape(event.description)}')
    if event.url:
        lines.append(f'URL:{event.url}')
    lines.append(f'STATUS:{event.status}')
    if event.alarm:
        lines += [
            'BEGIN:VALARM',
            'ACTION:DISPLAY',
            f'TRIGGER:{event.alarm}',
            f'DESCRIPTION:{escape(event.alarm_text or event.title)}',
            'END:VALARM',
        ]
    lines.append('END:VEVENT')
    return lines


def calendar(events, *, prodid: str, name: str = '') -> str:
    stamp = utc_stamp(timezone.now())
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', f'PRODID:{prodid}', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH']
    if name:
        lines.append(f'X-WR-CALNAME:{escape(name)}')
    for event in events:
        lines += _event_lines(event, stamp)
    lines.append('END:VCALENDAR')
    return '\r\n'.join(fold(line) for line in lines) + '\r\n'


def ics_response(content: str, filename: str, *, attachment: bool = True) -> HttpResponse:
    response = HttpResponse(content, content_type='text/calendar; charset=utf-8')
    disposition = 'attachment' if attachment else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    response['Cache-Control'] = 'private, no-store'
    return response
