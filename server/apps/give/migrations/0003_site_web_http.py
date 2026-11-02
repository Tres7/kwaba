from django.db import migrations, models

import apps.give.models


class Migration(migrations.Migration):

    dependencies = [
        ('give', '0002_comptes_par_identifiant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisationmodel',
            name='site_web',
            field=models.URLField(blank=True, validators=[apps.give.models.valider_site_web]),
        ),
    ]
