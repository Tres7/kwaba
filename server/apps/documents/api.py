from types import SimpleNamespace

from django.db.models import Exists
from django.db.models.functions import Trim

from .generateurs import nom
from .models import ParametresSocieteModel, stockage_prive
from .pdf import Document, _p as paragraphe, date, fcfa
from .registre import Produit, enregistrer
from .services import pieces_confirmation

__all__ = ['Document', 'Produit', 'date', 'enregistrer', 'fcfa', 'nom', 'paragraphe', 'pieces_confirmation', 'societe',
           'societe_immatriculee', 'stockage_prive', 'condition_societe_immatriculee']


def societe() -> SimpleNamespace:
    """Legal information of Kwa-Ba (read only), with its `complets` and `immatriculee` states."""
    s = ParametresSocieteModel.courants()
    return SimpleNamespace(**{f.name: getattr(s, f.name) for f in s._meta.concrete_fields},
                           complets=s.complets, immatriculee=s.immatriculee)


def societe_immatriculee() -> bool:
    """One read, never a write (courants() would create the row, for example during a public request)."""
    societe = ParametresSocieteModel.objects.filter(pk=1).first()
    return bool(societe and societe.immatriculee)


def condition_societe_immatriculee() -> Exists:
    """Same rule as societe_immatriculee, as a SQL condition (no query when a queryset is built)."""
    return Exists(
        ParametresSocieteModel.objects.filter(pk=1)
        .annotate(_raison=Trim('raison_sociale'), _adresse=Trim('adresse'), _rccm=Trim('rccm'), _nif=Trim('nif'))
        .exclude(_raison='').exclude(_adresse='').exclude(_rccm='').exclude(_nif='')
    )
