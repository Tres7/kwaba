import re

from gunicorn.glogging import Logger

JETON_SIGNATURE = re.compile(r'(/contrats/signature/)[^/?\s"]+')


def sans_jeton(valeur: str) -> str:
    return JETON_SIGNATURE.sub(r'\1***', valeur)


class JournalSansJeton(Logger):
    """Access log without the token of the signature links, which gives access to the contract (same rule as nginx)."""

    def atoms(self, resp, req, environ, request_time):
        atomes = super().atoms(resp, req, environ, request_time)
        for cle in ('r', 'U', 'f'):
            atomes[cle] = sans_jeton(atomes[cle])
        return atomes
