from apps.activity.application.service import ActivityService
from apps.activity.infrastructure.clock import DjangoClock
from apps.activity.infrastructure.lookups import DjangoPeopleLookup
from apps.activity.infrastructure.persistence.repositories import DjangoEntryRepository


def activity_service() -> ActivityService:
    return ActivityService(entries=DjangoEntryRepository(), people=DjangoPeopleLookup(), clock=DjangoClock())
