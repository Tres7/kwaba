import django.db.models.deletion
from django.db import migrations, models

# (model, field, target, related_name, one to one, nullable)
CLES = [
    ('paiementmodel', 'reservation', 'reservations.reservationmodel', 'paiements', False, True),
    ('paiementmodel', 'transfert', 'transferts.transfertmodel', 'paiements', False, True),
    ('paiementmodel', 'don', 'give.donmodel', 'paiements', False, True),
    ('paiementmodel', 'location', 'locations.locationmodel', 'paiements', False, True),
    ('remboursementmodel', 'reservation', 'reservations.reservationmodel', 'remboursements', False, True),
    ('remboursementmodel', 'transfert', 'transferts.transfertmodel', 'remboursements', False, True),
    ('remboursementmodel', 'location', 'locations.locationmodel', 'remboursements', False, True),
    ('versementmodel', 'reservation', 'reservations.reservationmodel', 'versement', True, False),
]


def _ancien_champ(cible, related_name, un_a_un, nullable):
    classe = models.OneToOneField if un_a_un else models.ForeignKey
    options = {'null': True, 'blank': True} if nullable else {}
    return classe(db_constraint=False, on_delete=django.db.models.deletion.PROTECT, related_name=related_name, to=cible,
                  **options)


def _nouveau_champ(un_a_un, nullable):
    if un_a_un:
        return models.UUIDField(unique=True)
    return models.UUIDField(blank=True, db_index=True, null=True) if nullable else models.UUIDField(db_index=True)


def _un_seul_objet(suffixe):
    champs = ('reservation', 'transfert', 'don', 'location')
    condition = None
    for rempli in champs:
        q = models.Q(**{f'{c}{suffixe}__isnull': c != rempli for c in champs})
        condition = q if condition is None else condition | q
    return models.CheckConstraint(condition=condition, name='paiement_un_seul_objet')


class Migration(migrations.Migration):

    dependencies = [
        ('paiements', '0007_conditions_hote'),
        ('give', '0001_initial'),
        ('locations', '0001_initial'),
        ('reservations', '0002_reservationmodel_annule_le_and_more'),
        ('transferts', '0002_aeroports_tarifs'),
    ]

    operations = [
        *[migrations.AlterField(model_name=modele, name=champ, field=_ancien_champ(cible, related_name, un_a_un, nullable))
          for modele, champ, cible, related_name, un_a_un, nullable in CLES],
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveConstraint(model_name='paiementmodel', name='paiement_un_seul_objet'),
                *[operation for modele, champ, _, _, un_a_un, nullable in CLES for operation in (
                    migrations.RemoveField(model_name=modele, name=champ),
                    migrations.AddField(model_name=modele, name=f'{champ}_id', field=_nouveau_champ(un_a_un, nullable),
                                        preserve_default=False),
                )],
                migrations.AddConstraint(model_name='paiementmodel', constraint=_un_seul_objet('_id')),
            ],
        ),
    ]
