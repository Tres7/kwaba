import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transferts', '0004_chauffeur_excellence'),
        ('reservations', '0002_reservationmodel_annule_le_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transfertmodel',
            name='reservation',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text='Séjour Kwa-Ba associé (facultatif)',
                                    null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transferts',
                                    to='reservations.reservationmodel'),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='transfertmodel', name='reservation'),
                migrations.AddField(model_name='transfertmodel', name='reservation_id',
                                    field=models.UUIDField(blank=True, db_index=True, help_text='Séjour Kwa-Ba associé (facultatif)',
                                                           null=True)),
            ],
        ),
    ]
