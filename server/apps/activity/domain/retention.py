from datetime import datetime, timedelta

RETENTION = timedelta(days=365)


def purge_before(now: datetime) -> datetime:
    return now - RETENTION
