from types import SimpleNamespace

from .generateurs import nom
from .models import ParametresSocieteModel, stockage_prive
from .pdf import Document, _p as paragraphe, date, fcfa
from .registre import Produit, enregistrer
from .services import pieces_confirmation

__all__ = ['Document', 'Produit', 'date', 'enregistrer', 'fcfa', 'nom', 'paragraphe', 'pieces_confirmation', 'societe',
           'societe_immatriculee', 'stockage_prive']


def societe() -> SimpleNamespace:
    """Legal information of Kwa-Ba (read only), with its `complets` and `immatriculee` states."""
    s = ParametresSocieteModel.courants()
    return SimpleNamespace(**{f.name: getattr(s, f.name) for f in s._meta.concrete_fields},
                           complets=s.complets, immatriculee=s.immatriculee)


def societe_immatriculee() -> bool:
    return ParametresSocieteModel.courants().immatriculee
