"""Kwa-Ba taxonomy (brief AN-TAX of 2026-11-03): maison becomes maison_entiere, hotel becomes chambre_hotel, and a
private room in a house, flat or villa becomes the type chambre_privee. Résidence and auberge stay as they are."""
from django.db import migrations, models

ANCIENS = {'maison': 'maison_entiere', 'hotel': 'chambre_hotel'}
LOGEMENTS = ('maison', 'appartement', 'villa', 'maison_entiere')


def nouveau_type(type_, espace):
    if espace == 'chambre_privee' and type_ in LOGEMENTS:
        return 'chambre_privee'
    return ANCIENS.get(type_, type_)


def vers_taxonomie(apps, schema_editor):
    Hebergement = apps.get_model('hebergements', 'HebergementModel')
    for h in Hebergement.objects.all().only('id', 'type', 'espace'):
        type_ = nouveau_type(h.type, h.espace)
        espace = 'chambre_privee' if type_ == 'chambre_privee' else 'entier'
        if (type_, espace) != (h.type, h.espace):
            Hebergement.objects.filter(pk=h.pk).update(type=type_, espace=espace)

    Brouillon = apps.get_model('hebergements', 'BrouillonAnnonceModel')
    for b in Brouillon.objects.all():
        donnees = dict(b.donnees or {})
        if donnees.get('type'):
            donnees['type'] = nouveau_type(donnees['type'], donnees.get('espace'))
        donnees.pop('espace', None)
        donnees.pop('surface_m2', None)
        # The "espace" screen of the wizard no longer exists: the type says it
        etape = 'adresse' if b.etape == 'espace' else b.etape
        if donnees != b.donnees or etape != b.etape:
            Brouillon.objects.filter(pk=b.pk).update(donnees=donnees, etape=etape)


def vers_anciens_types(apps, schema_editor):
    Hebergement = apps.get_model('hebergements', 'HebergementModel')
    Hebergement.objects.filter(type='maison_entiere').update(type='maison')
    Hebergement.objects.filter(type='chambre_hotel').update(type='hotel')
    Hebergement.objects.filter(type='studio').update(type='appartement')
    Hebergement.objects.filter(type='chambre_privee').update(type='appartement', espace='chambre_privee')


class Migration(migrations.Migration):

    dependencies = [
        ('hebergements', '0017_envoi_annonce'),
    ]

    operations = [
        migrations.AddField(
            model_name='hebergementmodel',
            name='point_repere',
            field=models.CharField(blank=True, db_default='', default='', max_length=200),
        ),
        migrations.AlterField(
            model_name='hebergementmodel',
            name='type',
            field=models.CharField(choices=[('chambre_privee', 'Chambre privée'), ('studio', 'Studio'),
                                            ('appartement', 'Appartement'), ('maison_entiere', 'Maison entière'),
                                            ('villa', 'Villa'), ('chambre_hotel', "Chambre d'hôtel"),
                                            ('residence', 'Résidence hôtelière'), ('auberge', 'Auberge')],
                                   default='chambre_hotel', max_length=50),
        ),
        migrations.RunPython(vers_taxonomie, vers_anciens_types),
    ]
