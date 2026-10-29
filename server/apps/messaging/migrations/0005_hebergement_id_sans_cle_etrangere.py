import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0004_masquer_anciens_messages'),
        ('hebergements', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conversationmodel',
            name='hebergement',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='conversations', to='hebergements.hebergementmodel'),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveConstraint(model_name='conversationmodel', name='messaging_unique_hebergement_guest'),
                migrations.RemoveField(model_name='conversationmodel', name='hebergement'),
                migrations.AddField(model_name='conversationmodel', name='hebergement_id',
                                    field=models.UUIDField(db_index=True), preserve_default=False),
                migrations.AddConstraint(
                    model_name='conversationmodel',
                    constraint=models.UniqueConstraint(fields=('hebergement_id', 'guest'),
                                                       name='messaging_unique_hebergement_guest'),
                ),
            ],
        ),
    ]
