import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('verifications', '0001_initial'),
        ('hebergements', '0005_verification_des_annonces'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visitemodel',
            name='hebergement',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='visites', to='hebergements.hebergementmodel'),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='visitemodel', name='hebergement'),
                migrations.AddField(model_name='visitemodel', name='hebergement_id',
                                    field=models.UUIDField(db_index=True), preserve_default=False),
            ],
        ),
    ]
