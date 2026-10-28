"""Every existing booking points to the default unit type of its establishment (created by hebergements 0010)."""
from django.db import migrations
from django.db.models import OuterRef, Subquery


def rattacher(apps, schema_editor):
    Reservation = apps.get_model('reservations', 'ReservationModel')
    TypeLogement = apps.get_model('hebergements', 'TypeLogementModel')
    premier_type = TypeLogement.objects.filter(hebergement_id=OuterRef('hebergement_id')).order_by('ordre', 'prix_nuit', 'created_at')
    Reservation.objects.filter(type_logement__isnull=True).update(type_logement_id=Subquery(premier_type.values('id')[:1]))


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0005_type_logement_et_unites'),
        ('hebergements', '0010_types_par_defaut'),
    ]

    operations = [migrations.RunPython(rattacher, migrations.RunPython.noop)]
