from django.apps import apps
from django.core.management.base import BaseCommand
from django.db.models import FileField


def champs_prives():
    """File fields of every module stored in settings.STORAGES['prive'] (their storage is a `stockage_prive` function)."""
    for modele in apps.get_models():
        for champ in modele._meta.get_fields():
            if isinstance(champ, FileField) and getattr(getattr(champ, '_storage_callable', None), '__name__', '') == 'stockage_prive':
                yield modele, champ


class Command(BaseCommand):
    help = ("Fichiers privés (pièces d'identité, contrats, factures, photos de visite) cités par la base mais absents du "
            "stockage. Lecture seule.")

    def handle(self, *args, **options):
        perdus = 0
        for modele, champ in champs_prives():
            objets = modele.objects.exclude(**{champ.name: ''}).exclude(**{f'{champ.name}__isnull': True})
            manquants = [o for o in objets if not champ.storage.exists(getattr(o, champ.name).name)]
            perdus += len(manquants)
            self.stdout.write(f"{modele._meta.label}.{champ.name} : {objets.count()} fichier(s), {len(manquants)} introuvable(s)")
            for objet in manquants:
                self.stdout.write(f"  - {objet.pk} · {objet}")
        style = self.style.WARNING if perdus else self.style.SUCCESS
        self.stdout.write(style(f"{perdus} fichier(s) introuvable(s)."))
