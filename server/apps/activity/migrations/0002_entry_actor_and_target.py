import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0001_initial'),
        ('securite', '0016_move_audit_log_to_activity'),
    ]

    operations = [
        migrations.RenameField(model_name='activityentrymodel', old_name='cree_le', new_name='created_at'),
        migrations.RenameField(model_name='activityentrymodel', old_name='utilisateur_id', new_name='actor_id'),
        migrations.RenameField(model_name='activityentrymodel', old_name='email', new_name='actor_email'),
        migrations.AlterField(
            model_name='activityentrymodel', name='created_at',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='activityentrymodel', name='action',
            field=models.CharField(db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name='activityentrymodel', name='actor_role',
            field=models.CharField(blank=True, db_default='', default='', max_length=20),
        ),
        migrations.AddField(
            model_name='activityentrymodel', name='target_kind',
            field=models.CharField(blank=True, db_default='', default='', max_length=20),
        ),
        migrations.AddField(
            model_name='activityentrymodel', name='target_id',
            field=models.CharField(blank=True, db_default='', default='', max_length=64),
        ),
        migrations.AddField(
            model_name='activityentrymodel', name='target_label',
            field=models.CharField(blank=True, db_default='', default='', max_length=255),
        ),
        migrations.AddField(
            model_name='activityentrymodel', name='legacy',
            field=models.BooleanField(db_default=False, default=False),
        ),
        migrations.AlterModelTable(name='activityentrymodel', table='activity_entry'),
        migrations.AlterModelOptions(
            name='activityentrymodel',
            options={'ordering': ['-created_at', '-id'], 'verbose_name': "Entrée du journal d'activité",
                     'verbose_name_plural': "Journal d'activité"},
        ),
        migrations.AddIndex(
            model_name='activityentrymodel',
            index=models.Index(fields=['target_kind', 'target_id'], name='activity_entry_target'),
        ),
        migrations.CreateModel(
            name='ActivityHoldModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target_kind', models.CharField(max_length=20)),
                ('target_id', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={'db_table': 'activity_hold'},
        ),
        migrations.AddConstraint(
            model_name='activityholdmodel',
            constraint=models.UniqueConstraint(fields=('target_kind', 'target_id'), name='activity_one_hold_per_target'),
        ),
    ]
