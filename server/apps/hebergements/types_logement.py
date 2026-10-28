"""Unit types of an establishment (TypeLogementModel).

Until hosts manage several types themselves, every establishment has one default type that mirrors the listing:
same price, same capacity, quantity 1. That is exactly the former "one listing = one unit" model, so nothing
changes for travellers or hosts while the rest of the code moves to unit types.
"""
from .models import HebergementModel, TypeLogementModel

# Name of the default type, by kind of establishment
NOMS_PAR_DEFAUT = {
    'hotel': 'Chambre',
    'auberge': 'Chambre',
    'residence': 'Appartement',
    'appartement': 'Appartement entier',
    'villa': 'Logement entier',
    'maison': 'Logement entier',
}


def nom_par_defaut(type_etablissement: str) -> str:
    return NOMS_PAR_DEFAUT.get(type_etablissement, 'Logement entier')


def assurer_type_par_defaut(hebergement: HebergementModel) -> TypeLogementModel:
    """Creates the default type if the establishment has none; with a single type, keeps it in line with the
    listing's price and capacity (edited in the host's form). Returns the establishment's first type."""
    types = list(hebergement.types.all()[:2])
    if not types:
        return TypeLogementModel.objects.create(
            hebergement=hebergement, nom=nom_par_defaut(hebergement.type), capacite=max(1, hebergement.max_guests),
            prix_nuit=hebergement.price_per_night, quantite=1,
        )
    if len(types) == 1:
        seul = types[0]
        capacite = max(1, hebergement.max_guests)
        if seul.prix_nuit != hebergement.price_per_night or seul.capacite != capacite:
            seul.prix_nuit, seul.capacite = hebergement.price_per_night, capacite
            seul.save(update_fields=['prix_nuit', 'capacite', 'updated_at'])
    return types[0]


def type_par_defaut(hebergement: HebergementModel) -> TypeLogementModel:
    """The type booked when none is chosen: the establishment's first active type (created if missing)."""
    return hebergement.types.filter(actif=True).first() or assurer_type_par_defaut(hebergement)


def type_par_defaut_id(hebergement_id):
    """Id of the type booked when none is chosen, from the establishment's id."""
    trouve = TypeLogementModel.objects.filter(hebergement_id=hebergement_id, actif=True).values_list('id', flat=True).first()
    return trouve or type_par_defaut(HebergementModel.objects.get(pk=hebergement_id)).id
