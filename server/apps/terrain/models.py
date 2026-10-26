import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class MissionModel(models.Model):
    """An agent taking charge of a check, in the shared queue of the field agents.

    What needs checking comes from each domain (listings to visit, identity documents…, see types.py): a
    mission is born when an agent says "I'll handle it". While it is ongoing, no other agent can take it
    nor decide in their place; only an administrator can release it or decide anyway.
    """
    TYPES = [
        ('logement', 'Visite de logement'),
        ('piece', "Pièce d'identité"),
    ]
    STATUTS = [('en_cours', 'En cours'), ('terminee', 'Terminée'), ('liberee', 'Relâchée')]
    DECISIONS = [('validee', 'Validée'), ('refusee', 'Refusée')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=20, choices=TYPES)
    # Id of what is checked, depending on the type: listing (stay), host (identity document)
    cible = models.CharField(max_length=64)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                              related_name='missions_terrain')
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_cours')
    decision = models.CharField(max_length=20, choices=DECISIONS, blank=True)
    # Copy at the time it was taken: the history stays readable even if the listing changes or disappears
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
            # A single agent at a time on the same check
            models.UniqueConstraint(fields=['type', 'cible'], condition=Q(statut='en_cours'), name='mission_une_seule_en_cours'),
        ]
        indexes = [models.Index(fields=['agent', 'statut'])]

    def __str__(self):
        return f"{self.get_type_display()} · {self.titre} ({self.get_statut_display().lower()})"
