import pytest


@pytest.fixture(autouse=True)
def grille_sans_base(monkeypatch):
    """Unit tests have no database: the rates in force are those of the grid of 18 October 2026 (the defaults of an
    unsaved ReglagesTarifsModel row)."""
    from apps.paiements import tarifs
    from apps.paiements.models import ReglagesTarifsModel

    monkeypatch.setattr(tarifs, 'reglages', lambda: ReglagesTarifsModel())
