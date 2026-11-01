"""Experiences of the Discover page: activities, restaurants, leisure and sites, managed from the back-office."""
from django.db import models


class ExperienceModel(models.Model):
    CATEGORIES = [
        ('activites', 'Activité'),
        ('restaurants', 'Restaurant'),
        ('loisirs', 'Loisir'),
        ('sites', 'Site touristique'),
    ]

    categorie = models.CharField(max_length=20, choices=CATEGORIES, db_index=True)
    nom = models.CharField(max_length=120)
    nom_en = models.CharField(max_length=120, blank=True, help_text='Vide : le nom français est affiché')
    etiquette = models.CharField(max_length=40, help_text='Par ex. « Culture », « Plage », « Ivoirien »')
    etiquette_en = models.CharField(max_length=40, blank=True)
    ville = models.CharField(max_length=100, db_index=True)
    pays = models.CharField(max_length=100)
    pays_en = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    description_en = models.TextField(blank=True)
    prix = models.PositiveIntegerField(null=True, blank=True, help_text='FCFA, indicatif. Vide : pas de prix affiché')
    gratuit = models.BooleanField(default=False)
    image = models.ImageField(upload_to='experiences/', blank=True)
    # Photo of the seeded guide (external address, or path served by the website); a photo uploaded from the
    # back-office replaces it
    image_url = models.URLField(max_length=500, blank=True)
    # Required by the Creative Commons licences of the seeded photos: author and licence, link to the source
    credit_photo = models.CharField(max_length=160, blank=True, help_text='Auteur et licence, si la photo n\'est pas à Kwa-Ba')
    credit_photo_url = models.URLField(max_length=500, blank=True)
    actif = models.BooleanField(default=True, help_text='Affichée sur la page Découvrir')
    ordre = models.PositiveSmallIntegerField(default=0)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ordre', 'id']
        verbose_name = 'Expérience'
        verbose_name_plural = 'Expériences'

    def __str__(self):
        return f"{self.nom} ({self.ville})"

    def photo(self, request=None) -> str | None:
        if self.image:
            return request.build_absolute_uri(self.image.url) if request else self.image.url
        return self.image_url or None
