"""One default unit type per existing establishment: same price and capacity as the listing, quantity 1.

Exactly the former "one listing = one unit" model: nothing changes for travellers or hosts. Additive only.
"""
from django.db import migrations

NOMS_PAR_DEFAUT = {
    'hotel': 'Chambre', 'auberge': 'Chambre', 'residence': 'Appartement', 'appartement': 'Appartement entier',
    'villa': 'Logement entier', 'maison': 'Logement entier',
}


def creer_types_par_defaut(apps, schema_editor):
    Hebergement = apps.get_model('hebergements', 'HebergementModel')
    TypeLogement = apps.get_model('hebergements', 'TypeLogementModel')
    sans_type = Hebergement.objects.filter(types__isnull=True)
    TypeLogement.objects.bulk_create([
        TypeLogement(hebergement_id=h.id, nom=NOMS_PAR_DEFAUT.get(h.type, 'Logement entier'), capacite=max(1, h.max_guests),
                     prix_nuit=h.price_per_night, quantite=1)
        for h in sans_type.only('id', 'type', 'max_guests', 'price_per_night').iterator()
    ], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [('hebergements', '0009_types_de_logement')]

    operations = [migrations.RunPython(creer_types_par_defaut, migrations.RunPython.noop)]
