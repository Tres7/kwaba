import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('voyages', '0001_initial'),
        ('hebergements', '0004_blocagemodel'),
        ('reservations', '0002_reservationmodel_annule_le_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='propositionmodel',
            name='hebergement',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='+',
                                    to='hebergements.hebergementmodel'),
        ),
        migrations.AlterField(
            model_name='lienreservationmodel',
            name='reservation',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='+',
                                    to='reservations.reservationmodel'),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveConstraint(model_name='propositionmodel', name='proposition_unique'),
                migrations.RemoveField(model_name='propositionmodel', name='hebergement'),
                migrations.AddField(model_name='propositionmodel', name='hebergement_id',
                                    field=models.UUIDField(db_index=True), preserve_default=False),
                migrations.AddConstraint(
                    model_name='propositionmodel',
                    constraint=models.UniqueConstraint(fields=('voyage', 'hebergement_id'), name='proposition_unique'),
                ),
                migrations.RemoveConstraint(model_name='lienreservationmodel', name='reservation_partagee_unique'),
                migrations.RemoveField(model_name='lienreservationmodel', name='reservation'),
                migrations.AddField(model_name='lienreservationmodel', name='reservation_id',
                                    field=models.UUIDField(db_index=True), preserve_default=False),
                migrations.AddConstraint(
                    model_name='lienreservationmodel',
                    constraint=models.UniqueConstraint(fields=('voyage', 'reservation_id'),
                                                       name='reservation_partagee_unique'),
                ),
            ],
        ),
    ]
