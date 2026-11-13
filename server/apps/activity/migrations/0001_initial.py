from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('securite', '0015_moderation'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='ActivityEntryModel',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False,
                                                   verbose_name='ID')),
                        ('cree_le', models.DateTimeField(auto_now_add=True, db_index=True)),
                        ('action', models.CharField(db_index=True, max_length=40)),
                        ('utilisateur_id', models.UUIDField(blank=True, db_index=True, null=True)),
                        ('email', models.CharField(blank=True, max_length=254)),
                        ('ip', models.GenericIPAddressField(blank=True, null=True)),
                        ('details', models.JSONField(blank=True, default=dict)),
                    ],
                    options={'db_table': 'securite_journal_audit', 'ordering': ['-cree_le']},
                ),
            ],
            database_operations=[],
        ),
    ]
