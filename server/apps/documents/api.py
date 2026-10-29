from .models import ParametresSocieteModel


def societe_immatriculee() -> bool:
    return ParametresSocieteModel.courants().immatriculee
