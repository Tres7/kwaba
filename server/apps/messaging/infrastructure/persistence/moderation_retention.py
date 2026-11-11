import datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.messaging.infrastructure.persistence.models import MessageReportModel, SanctionModel
from apps.securite import fraude


def _days(key: str) -> datetime.timedelta:
    return datetime.timedelta(days=settings.MODERATION[key])


def purge(now: datetime.datetime | None = None) -> dict:
    now = now or timezone.now()
    reports = MessageReportModel.objects.filter(legal_hold=False)
    with transaction.atomic():
        stats = {
            'rejected_context': reports.filter(status='rejected', reviewed_at__lt=now - _days('REJECTED_REPORT_RETENTION_DAYS'))
            .exclude(context=[], details='').update(context=[], details=''),
            'rejected_rows': reports.filter(status='rejected', reviewed_at__lt=now - _days('REPORTER_COUNTER_RETENTION_DAYS'))
            .delete()[0],
            'confirmed_context': reports.filter(status='confirmed', reviewed_at__lt=now - _days('CONFIRMED_REPORT_RETENTION_DAYS'))
            .exclude(context=[], details='').update(context=[], details=''),
            'contest_text': SanctionModel.objects.filter(created_at__lt=now - _days('CONFIRMED_REPORT_RETENTION_DAYS'))
            .exclude(contest_text='').update(contest_text=''),
            'sanctions': SanctionModel.objects.filter(created_at__lt=now - _days('SANCTION_RETENTION_DAYS'))
            .exclude(report_id__in=MessageReportModel.objects.filter(legal_hold=True).values('id')).delete()[0],
            'confirmed_rows': reports.filter(status='confirmed', reviewed_at__lt=now - _days('SANCTION_RETENTION_DAYS'))
            .delete()[0],
            'excerpts': fraude.purge_moderation_excerpts(now),
        }
    stats['threat_alerts'] = fraude.flush_threat_alerts()
    return {k: v for k, v in stats.items() if v}
