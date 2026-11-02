from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('experiences', '0002_guide_initial')]

    operations = [
        migrations.AddField(
            model_name='experiencemodel',
            name='credit_photo',
            field=models.CharField(blank=True, help_text="Auteur et licence, si la photo n'est pas à Kwa-Ba", max_length=160),
        ),
        migrations.AddField(
            model_name='experiencemodel',
            name='credit_photo_url',
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
