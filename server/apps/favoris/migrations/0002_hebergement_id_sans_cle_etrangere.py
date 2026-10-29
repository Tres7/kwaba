import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('favoris', '0001_initial'),
        ('hebergements', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='favorimodel',
            name='hebergement',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='favorited_by', to='hebergements.hebergementmodel'),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveConstraint(model_name='favorimodel', name='unique_user_hebergement_favori'),
                migrations.RemoveField(model_name='favorimodel', name='hebergement'),
                migrations.AddField(model_name='favorimodel', name='hebergement_id',
                                    field=models.UUIDField(db_index=True), preserve_default=False),
                migrations.AddConstraint(
                    model_name='favorimodel',
                    constraint=models.UniqueConstraint(fields=('user', 'hebergement_id'),
                                                       name='unique_user_hebergement_favori'),
                ),
            ],
        ),
    ]
