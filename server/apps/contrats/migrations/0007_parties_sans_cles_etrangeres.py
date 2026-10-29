import django.db.models.deletion
from django.db import migrations, models


def _contrainte(champ, nom):
    return models.UniqueConstraint(
        condition=models.Q(models.Q(('statut', 'annule'), _negated=True), (f'{champ}__isnull', False)),
        fields=(champ,), name=nom,
    )


PARTIES = [
    ('chauffeur', 'transferts.chauffeurmodel', 'un_contrat_par_chauffeur', models.BigIntegerField),
    ('loueur', 'locations.partenairelocationmodel', 'un_contrat_par_loueur', models.BigIntegerField),
    ('organisation', 'give.organisationmodel', 'un_contrat_par_ong', models.UUIDField),
]


class Migration(migrations.Migration):

    dependencies = [
        ('contrats', '0006_contrat_hotel_textes_octobre'),
        ('give', '0001_initial'),
        ('locations', '0003_locationmodel_relance_paiement'),
        ('transferts', '0003_transfertmodel_relance_paiement'),
    ]

    operations = [
        *[migrations.AlterField(
            model_name='contratmodel',
            name=champ,
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='contrats', to=cible),
        ) for champ, cible, _, _ in PARTIES],
        migrations.SeparateDatabaseAndState(
            state_operations=[
                operation
                for champ, _, contrainte, type_champ in PARTIES
                for operation in (
                    migrations.RemoveConstraint(model_name='contratmodel', name=contrainte),
                    migrations.RemoveField(model_name='contratmodel', name=champ),
                    migrations.AddField(model_name='contratmodel', name=f'{champ}_id',
                                        field=type_champ(blank=True, db_index=True, null=True)),
                    migrations.AddConstraint(model_name='contratmodel', constraint=_contrainte(f'{champ}_id', contrainte)),
                )
            ],
        ),
    ]
