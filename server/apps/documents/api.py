from .generateurs import nom
from .models import ParametresSocieteModel
from .pdf import Document, date, fcfa
from .registre import Produit, enregistrer
from .services import pieces_confirmation

__all__ = ['Document', 'Produit', 'date', 'enregistrer', 'fcfa', 'nom', 'pieces_confirmation', 'societe_immatriculee']


def societe_immatriculee() -> bool:
    return ParametresSocieteModel.courants().immatriculee
