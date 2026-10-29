import django.db.models.deletion
from django.db import migrations, models

AIDE_RESERVATION = 'Séjour Kwa-Ba associé (facultatif) : avec un chauffeur, Pack Séjour (frais du logement à 3 %)'
AIDE_DEMANDE = '« Mon chauffeur » : chauffeur que le voyageur redemande'
AIDE_PARTENAIRE = 'Chauffeur partenaire de Kwa-Ba (formules avec chauffeur)'


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0007_vehicules_proprietaires'),
        ('reservations', '0003_reservationmodel_relance_paiement'),
        ('transferts', '0004_chauffeur_excellence'),
    ]

    operations = [
        migrations.AlterField(
            model_name='locationmodel', name='reservation',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text=AIDE_RESERVATION, null=True,
                                    on_delete=django.db.models.deletion.SET_NULL, related_name='locations',
                                    to='reservations.reservationmodel'),
        ),
        migrations.AlterField(
            model_name='locationmodel', name='chauffeur_demande',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text=AIDE_DEMANDE, null=True,
                                    on_delete=django.db.models.deletion.SET_NULL, related_name='+',
                                    to='transferts.chauffeurmodel'),
        ),
        migrations.AlterField(
            model_name='locationmodel', name='chauffeur_partenaire',
            field=models.ForeignKey(blank=True, db_constraint=False, help_text=AIDE_PARTENAIRE, null=True,
                                    on_delete=django.db.models.deletion.PROTECT, related_name='locations',
                                    to='transferts.chauffeurmodel'),
        ),
        migrations.AlterField(
            model_name='versementchauffeurlocationmodel', name='chauffeur',
            field=models.ForeignKey(db_constraint=False, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='versements_locations', to='transferts.chauffeurmodel'),
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(model_name='locationmodel', name='reservation'),
                migrations.AddField(model_name='locationmodel', name='reservation_id',
                                    field=models.UUIDField(blank=True, db_index=True, help_text=AIDE_RESERVATION, null=True)),
                migrations.RemoveField(model_name='locationmodel', name='chauffeur_demande'),
                migrations.AddField(model_name='locationmodel', name='chauffeur_demande_id',
                                    field=models.BigIntegerField(blank=True, db_index=True, help_text=AIDE_DEMANDE, null=True)),
                migrations.RemoveField(model_name='locationmodel', name='chauffeur_partenaire'),
                migrations.AddField(model_name='locationmodel', name='chauffeur_partenaire_id',
                                    field=models.BigIntegerField(blank=True, db_index=True, help_text=AIDE_PARTENAIRE, null=True)),
                migrations.RemoveField(model_name='versementchauffeurlocationmodel', name='chauffeur'),
                migrations.AddField(model_name='versementchauffeurlocationmodel', name='chauffeur_id',
                                    field=models.BigIntegerField(db_index=True), preserve_default=False),
            ],
        ),
    ]
