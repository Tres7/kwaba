import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0006_rattacher_type_logement'),
        ('hebergements', '0010_types_par_defaut'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservationmodel',
            name='hebergement',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='reservations', to='hebergements.hebergementmodel'),
        ),
        migrations.AlterField(
            model_name='reservationmodel',
            name='type_logement',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.RESTRICT,
                                    related_name='reservations', to='hebergements.typelogementmodel'),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='reservationmodel', name='hebergement'),
                migrations.AddField(model_name='reservationmodel', name='hebergement_id',
                                    field=models.UUIDField(db_index=True), preserve_default=False),
                migrations.RemoveField(model_name='reservationmodel', name='type_logement'),
                migrations.AddField(model_name='reservationmodel', name='type_logement_id',
                                    field=models.UUIDField(blank=True, db_index=True, null=True)),
            ],
        ),
    ]
