from django.utils import timezone

from apps.activity.application.ports import Clock


class DjangoClock(Clock):
    def now(self):
        return timezone.now()
