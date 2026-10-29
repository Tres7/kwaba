import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('avis', '0002_notes_issues_des_avis'),
        ('hebergements', '0003_hebergementphotomodel'),
        ('reservations', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='avismodel',
            name='hebergement',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE, related_name='avis',
                                    to='hebergements.hebergementmodel'),
        ),
        migrations.AlterField(
            model_name='avismodel',
            name='reservation',
            field=models.OneToOneField(db_constraint=False, on_delete=django.db.models.deletion.CASCADE,
                                       related_name='avis', to='reservations.reservationmodel'),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='avismodel', name='hebergement'),
                migrations.AddField(model_name='avismodel', name='hebergement_id',
                                    field=models.UUIDField(db_index=True), preserve_default=False),
                migrations.RemoveField(model_name='avismodel', name='reservation'),
                migrations.AddField(model_name='avismodel', name='reservation_id',
                                    field=models.UUIDField(unique=True), preserve_default=False),
            ],
        ),
    ]
