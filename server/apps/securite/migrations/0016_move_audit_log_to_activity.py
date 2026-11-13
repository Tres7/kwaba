from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('securite', '0015_moderation'),
        ('activity', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.DeleteModel(name='JournalAuditModel')],
            database_operations=[],
        ),
    ]
