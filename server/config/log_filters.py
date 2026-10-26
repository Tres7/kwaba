import logging


class SansSondeDeSante(logging.Filter):
    """No alert email for the health probe: polled every few seconds, it would send one email per
    call during a database outage (already reported by the hosting platform)."""

    def filter(self, record):
        requete = getattr(record, 'request', None)
        return getattr(requete, 'path', '') != '/api/health/'
