class MouvementRefuse(ValueError):
    """A movement the ledger refuses (unknown or inactive code, wrong direction, locked month…), in French."""


class RestitutionRefusee(ValueError):
    """A report that cannot be produced (unknown axis, month not given by its first day…), in French."""
