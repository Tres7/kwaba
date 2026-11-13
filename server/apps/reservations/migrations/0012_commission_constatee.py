# Ledger of the finance module (FIN-03): when the commission of a stay became Kwa-Ba's revenue, at the arrival.
# The existing bookings are marked at once: their payments are older than the ledger, which has none of their lines.

from django.db import migrations, models
from django.db.models.functions import Now


def marquer_les_reservations_existantes(apps, schema_editor):
    apps.get_model('reservations', 'ReservationModel').objects.update(commission_constatee_le=Now())


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0011_demandes_paiement_tiers'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservationmodel',
            name='commission_constatee_le',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(marquer_les_reservations_existantes, migrations.RunPython.noop),
    ]
