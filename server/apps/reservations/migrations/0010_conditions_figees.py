"""Stay terms frozen on the booking (cancellation policy, hours, breakfast).

The bookings made before receive the values of their listing on the day of the migration: the closest to what the
traveller accepted, the history of the listing not being kept. Columns with a database default: the old code, which
still runs a few seconds after the migration, can keep creating bookings.
"""
from django.db import migrations, models


def figer(apps, schema_editor):
    Reservation = apps.get_model('reservations', 'ReservationModel')
    Hebergement = apps.get_model('hebergements', 'HebergementModel')
    ids = set(Reservation.objects.values_list('hebergement_id', flat=True))
    champs = ('politique_annulation', 'arrivee_a_partir', 'depart_avant', 'petit_dejeuner', 'petit_dejeuner_prix')
    for h in Hebergement._base_manager.filter(pk__in=ids).only('pk', *champs):
        Reservation.objects.filter(hebergement_id=h.pk).update(
            politique_annulation=h.politique_annulation or '', arrivee_a_partir=h.arrivee_a_partir,
            depart_avant=h.depart_avant, petit_dejeuner=h.petit_dejeuner or '', petit_dejeuner_prix=h.petit_dejeuner_prix,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0009_frais_menage'),
        ('hebergements', '0020_fermetures_partielles'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservationmodel',
            name='politique_annulation',
            field=models.CharField(blank=True, db_default='', default='', max_length=10),
        ),
        migrations.AddField(
            model_name='reservationmodel',
            name='arrivee_a_partir',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservationmodel',
            name='depart_avant',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservationmodel',
            name='petit_dejeuner',
            field=models.CharField(blank=True, db_default='', default='', max_length=10),
        ),
        migrations.AddField(
            model_name='reservationmodel',
            name='petit_dejeuner_prix',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(figer, migrations.RunPython.noop),
    ]
