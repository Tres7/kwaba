"""Kwa-Ba Together: planning a trip with several people (listings suggested and voted on, budget per
person, shared itinerary and bookings)."""
import secrets
import uuid

from django.db import models


def nouveau_code() -> str:
    return secrets.token_urlsafe(12)


class VoyageGroupeModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=80)
    destination = models.CharField(max_length=100, help_text='Ville')
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    nb_voyageurs = models.PositiveSmallIntegerField(default=2, help_text='Pour le budget par personne')
    organisateur_id = models.UUIDField(db_index=True)
    code_invitation = models.CharField(max_length=32, unique=True, default=nouveau_code)
    # Listing chosen by the organiser among the suggestions
    proposition_retenue = models.ForeignKey(
        'PropositionModel', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    notes = models.TextField(blank=True, help_text='Informations pratiques partagées (vols, rendez-vous…)')
    cree_le = models.DateTimeField(auto_now_add=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'voyages'
        ordering = ['-cree_le']
        verbose_name = 'Voyage de groupe'
        verbose_name_plural = 'Voyages de groupe'
        constraints = [models.CheckConstraint(
            condition=models.Q(date_fin__isnull=True) | models.Q(date_debut__isnull=True)
            | models.Q(date_fin__gt=models.F('date_debut')),
            name='voyage_fin_apres_debut',
        )]

    def __str__(self):
        return f"{self.nom} ({self.destination})"

    @property
    def nuits(self) -> int | None:
        if self.date_debut and self.date_fin:
            return (self.date_fin - self.date_debut).days
        return None


class MembreModel(models.Model):
    voyage = models.ForeignKey(VoyageGroupeModel, on_delete=models.CASCADE, related_name='membres')
    utilisateur_id = models.UUIDField(db_index=True)
    rejoint_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'voyages'
        ordering = ['rejoint_le']
        constraints = [models.UniqueConstraint(fields=['voyage', 'utilisateur_id'], name='membre_unique')]


class PropositionModel(models.Model):
    """A Kwa-Ba listing suggested to the group."""
    voyage = models.ForeignKey(VoyageGroupeModel, on_delete=models.CASCADE, related_name='propositions')
    hebergement_id = models.UUIDField(db_index=True)
    propose_par_id = models.UUIDField(db_index=True)
    commentaire = models.CharField(max_length=280, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'voyages'
        ordering = ['cree_le']
        constraints = [models.UniqueConstraint(fields=['voyage', 'hebergement_id'], name='proposition_unique')]


class VoteModel(models.Model):
    """Each member votes for a single listing (their favourite); they can change their mind."""
    voyage = models.ForeignKey(VoyageGroupeModel, on_delete=models.CASCADE, related_name='votes')
    proposition = models.ForeignKey(PropositionModel, on_delete=models.CASCADE, related_name='votes')
    utilisateur_id = models.UUIDField(db_index=True)

    class Meta:
        app_label = 'voyages'
        constraints = [models.UniqueConstraint(fields=['voyage', 'utilisateur_id'], name='un_vote_par_membre')]


class EtapeModel(models.Model):
    """A step of the shared itinerary."""
    voyage = models.ForeignKey(VoyageGroupeModel, on_delete=models.CASCADE, related_name='etapes')
    date = models.DateField()
    heure = models.TimeField(null=True, blank=True)
    titre = models.CharField(max_length=120)
    lieu = models.CharField(max_length=160, blank=True)
    details = models.CharField(max_length=500, blank=True)
    ajoute_par_id = models.UUIDField(db_index=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'voyages'
        ordering = ['date', models.F('heure').asc(nulls_first=True), 'cree_le']


class LienReservationModel(models.Model):
    """A member's Kwa-Ba booking, shared with the group."""
    voyage = models.ForeignKey(VoyageGroupeModel, on_delete=models.CASCADE, related_name='reservations')
    reservation_id = models.UUIDField(db_index=True)
    ajoute_par_id = models.UUIDField(db_index=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'voyages'
        ordering = ['cree_le']
        constraints = [models.UniqueConstraint(fields=['voyage', 'reservation_id'], name='reservation_partagee_unique')]
