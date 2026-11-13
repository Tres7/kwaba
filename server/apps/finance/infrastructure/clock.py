from django.utils import timezone

from apps.finance.application.ports import Clock


class DjangoClock(Clock):
    def now(self):
        return timezone.now()
