from decimal import Decimal

from . import tarifs


def total_sejour(prix_par_nuit: Decimal, nuits: int) -> int:
    return tarifs.calculer(prix_par_nuit, nuits).total
