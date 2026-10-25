import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class MissionModel(models.Model):
    """Prise en charge d'un contrôle par un agent, dans la file commune des agents de terrain.

    Ce qui est à contrôler vient de chaque domaine (annonces à visiter, pièces d'identité…, voir types.py) : une
    mission naît quand un agent dit « Je m'en occupe ». Tant qu'elle est en cours, aucun autre agent ne peut la
    prendre ni décider à sa place ; seul un administrateur peut la relâcher ou décider quand même.
    """
    TYPES = [
        ('logement', 'Visite de logement'),
        ('piece', "Pièce d'identité"),
    ]
    STATUTS = [('en_cours', 'En cours'), ('terminee', 'Terminée'), ('liberee', 'Relâchée')]
    DECISIONS = [('validee', 'Validée'), ('refusee', 'Refusée')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=20, choices=TYPES)
    # Identifiant de ce qui est contrôlé, selon le type : annonce (logement), hôte (pièce d'identité)
    cible = models.CharField(max_length=64)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                              related_name='missions_terrain')
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_cours')
    decision = models.CharField(max_length=20, choices=DECISIONS, blank=True)
    # Copie au moment de la prise : l'historique reste lisible même si l'annonce change ou disparaît
    titre = models.CharField(max_length=200)
    sous_titre = models.CharField(max_length=200, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    prise_le = models.DateTimeField(auto_now_add=True)
    terminee_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-prise_le']
        verbose_name = 'Mission de terrain'
        verbose_name_plural = 'Missions de terrain'
        constraints = [
            # Un seul agent à la fois sur un même contrôle
            models.UniqueConstraint(fields=['type', 'cible'], condition=Q(statut='en_cours'), name='mission_une_seule_en_cours'),
        ]
        indexes = [models.Index(fields=['agent', 'statut'])]

    def __str__(self):
        return f"{self.get_type_display()} · {self.titre} ({self.get_statut_display().lower()})"
