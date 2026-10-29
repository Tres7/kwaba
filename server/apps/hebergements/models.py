import uuid
from django.conf import settings
from django.db import models

from config import prelancement


def contrat_hote_exige() -> bool:
    """Once the company is registered (RCCM and NIF), a listing is public only if its host signed the agreement."""
    from apps.documents.api import societe_immatriculee  # local import: documents and contrats load the bookings

    return societe_immatriculee()


class HebergementQuerySet(models.QuerySet):
    def publiees(self):
        """Listings visible to the public: verified by a field agent and not hidden by the host."""
        if prelancement.actif():
            return self.none()  # pre-launch: verified listings wait for the opening
        # Once the company is registered, listings verified before wait for their host's signed agreement. The rule is
        # a SQL condition, evaluated by the database at each query: this queryset can be built at import time
        # (serializer fields), before the tables exist, and must follow a registration made while the API runs.
        from apps.contrats.api import condition_contrat_signe  # local import: contrats loads the payment rates
        from apps.documents.api import condition_societe_immatriculee

        return (self.filter(is_available=True, statut_verification='verifiee')
                .filter(~condition_societe_immatriculee() | condition_contrat_signe('host')))


class HebergementManager(models.Manager.from_queryset(HebergementQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(archivee_le__isnull=True)


class HebergementModel(models.Model):
    STATUTS_VERIFICATION = [
        ('en_attente', 'En attente de vérification'),
        ('verifiee', 'Vérifiée'),
        ('refusee', 'Refusée'),
    ]
    # Changing one of these fields after the visit puts the listing back into verification (what the agent checked)
    CHAMPS_VERIFIES = ('city', 'location', 'image_url', 'images')

    TYPE_CHOICES = [
        ('hotel', 'Hôtel'),
        ('villa', 'Villa'),
        ('maison', 'Maison'),
        ('appartement', 'Appartement'),
        ('residence', 'Résidence hôtelière'),
        ('auberge', 'Auberge'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='hotel')
    city = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    rating = models.FloatField(default=0.0)
    review_count = models.IntegerField(default=0)
    image_url = models.URLField(blank=True)
    images = models.JSONField(default=list, blank=True)
    max_guests = models.PositiveIntegerField(default=4)
    # Details shown on the page; required for a new listing, empty for the oldest ones
    surface_m2 = models.PositiveIntegerField(null=True, blank=True)
    chambres = models.PositiveSmallIntegerField(null=True, blank=True)
    salles_de_bain = models.PositiveSmallIntegerField(null=True, blank=True)
    lits_doubles = models.PositiveSmallIntegerField(default=0)
    lits_simples = models.PositiveSmallIntegerField(default=0)
    canapes_lits = models.PositiveSmallIntegerField(default=0)
    PETIT_DEJEUNER = [('non', 'Non proposé'), ('inclus', 'Inclus'), ('option', 'En option')]
    petit_dejeuner = models.CharField(max_length=10, choices=PETIT_DEJEUNER, blank=True)
    petit_dejeuner_prix = models.PositiveIntegerField(null=True, blank=True, help_text='FCFA par personne et par jour (option)')
    arrivee_a_partir = models.TimeField(null=True, blank=True, help_text="Heure d'arrivée à partir de")
    depart_avant = models.TimeField(null=True, blank=True, help_text='Heure de départ au plus tard')
    # Cancellation policy chosen by the host (terms of sale, appendix 1): see apps/paiements/tarifs.py
    POLITIQUES_ANNULATION = [('souple', 'Souple'), ('moderee', 'Modérée'), ('ferme', 'Ferme')]
    politique_annulation = models.CharField(max_length=10, choices=POLITIQUES_ANNULATION, default='moderee', db_default='moderee')
    amenities = models.JSONField(default=list)
    is_available = models.BooleanField(default=True)
    # Published only after the visit of a field agent (apps.verifications)
    statut_verification = models.CharField(max_length=20, choices=STATUTS_VERIFICATION, default='en_attente', db_index=True)
    verifiee_le = models.DateTimeField(null=True, blank=True)
    motif_refus = models.TextField(blank=True)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hebergements',
    )
    archivee_le = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = HebergementManager()
    tous = HebergementQuerySet.as_manager()

    class Meta:
        app_label = 'hebergements'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.city})"

    @property
    def est_publiee(self) -> bool:
        if not (self.is_available and self.statut_verification == 'verifiee') or prelancement.actif():
            return False
        from apps.contrats.api import hote_a_signe

        return not contrat_hote_exige() or hote_a_signe(self.host_id)


def _photo_upload_path(instance, filename):
    # Name generated by the server: the file's original name is never reused
    return f"hebergements/{instance.owner_id}/{instance.id}.jpg"


class HebergementPhotoModel(models.Model):
    """Photo uploaded by a host. Its URL is then referenced in a listing's image_url / images."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hebergement_photos',
    )
    image = models.ImageField(upload_to=_photo_upload_path)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'hebergements'
        ordering = ['-created_at']

    def __str__(self):
        return f"Photo {self.id} ({self.owner_id})"


class TypeLogementModel(models.Model):
    """What a traveller books in an establishment: a unit type with its stock (Booking model).

    A house is an establishment with a single type of quantity 1; a 200-room hotel has a few types ("Double
    standard", "Suite"…) whose quantity is the number of identical units. The establishment (HebergementModel)
    keeps the address, general photos and amenities.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hebergement = models.ForeignKey(HebergementModel, on_delete=models.CASCADE, related_name='types')
    nom = models.CharField(max_length=120, help_text='Par ex. « Double standard », « Suite », « Logement entier »')
    description = models.TextField(blank=True)
    capacite = models.PositiveSmallIntegerField(default=2, help_text='Voyageurs par unité')
    prix_nuit = models.DecimalField(max_digits=10, decimal_places=2, help_text='Prix par nuit et par unité (FCFA)')
    quantite = models.PositiveSmallIntegerField(default=1, help_text="Nombre d'unités identiques")
    photos = models.JSONField(default=list, blank=True, help_text="Photos propres au type ; vides : celles de l'établissement")
    actif = models.BooleanField(default=True)
    ordre = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'hebergements'
        ordering = ['ordre', 'prix_nuit']
        verbose_name = 'Type de logement'
        verbose_name_plural = 'Types de logement'
        constraints = [
            models.CheckConstraint(condition=models.Q(quantite__gte=1), name='type_logement_quantite_positive'),
            models.CheckConstraint(condition=models.Q(capacite__gte=1), name='type_logement_capacite_positive'),
        ]

    def __str__(self):
        return f"{self.nom} × {self.quantite} ({self.hebergement})"


class BlocageModel(models.Model):
    """Period closed to booking by the host. Like a booking, `fin` is exclusive (departure day).

    Without a unit type, the whole establishment is closed; with one, only that type.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hebergement = models.ForeignKey(HebergementModel, on_delete=models.CASCADE, related_name='blocages')
    type_logement = models.ForeignKey(TypeLogementModel, on_delete=models.CASCADE, null=True, blank=True,
                                      related_name='blocages')
    debut = models.DateField()
    fin = models.DateField()
    motif = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'hebergements'
        ordering = ['debut']
        constraints = [
            models.CheckConstraint(check=models.Q(fin__gt=models.F('debut')), name='blocage_fin_apres_debut'),
        ]

    def __str__(self):
        return f"Blocage {self.hebergement_id} {self.debut} → {self.fin}"


class InscriptionLancementModel(models.Model):
    """Waiting list: visitors to notify by email when the first listings are online."""
    email = models.EmailField(unique=True)
    langue = models.CharField(max_length=2, default='fr')
    cree_le = models.DateTimeField(auto_now_add=True)
    prevenu_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-cree_le']
        verbose_name = "Inscription à l'ouverture des logements"

    def __str__(self):
        return self.email


def _jeton_alerte() -> str:
    import secrets
    return secrets.token_urlsafe(32)


class AlerteDisponibiliteModel(models.Model):
    """A traveller to notify by email when the dates of a full listing can be booked again.

    Signed-in traveller: active at once. Visitor without an account: active once the address is confirmed through the
    emailed link (double opt-in). Expires when the arrival date has passed; one email at most per alert.
    """
    STATUTS = [
        ('a_confirmer', 'Adresse à confirmer'),
        ('active', 'Active'),
        ('notifiee', 'Prévenu'),
        ('expiree', 'Expirée'),
        ('annulee', 'Désinscrit'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hebergement = models.ForeignKey(HebergementModel, on_delete=models.CASCADE, related_name='alertes')
    # None: any unit type of the establishment
    type_logement = models.ForeignKey(TypeLogementModel, on_delete=models.CASCADE, null=True, blank=True, related_name='alertes')
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
                                    related_name='alertes_disponibilite')
    email = models.EmailField()
    langue = models.CharField(max_length=2, default='fr')
    date_debut = models.DateField()
    date_fin = models.DateField()
    nb_unites = models.PositiveSmallIntegerField(default=1)
    statut = models.CharField(max_length=12, choices=STATUTS, default='a_confirmer')
    # Confirmation and unsubscribe links
    jeton = models.CharField(max_length=64, unique=True, default=_jeton_alerte, editable=False)
    # Set when dates of the listing may have become free: checked by the worker at its next pass
    a_verifier = models.BooleanField(default=False)
    confirmation_envoyee = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)
    notifiee_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'hebergements'
        ordering = ['-cree_le']
        verbose_name = 'Alerte de disponibilité'
        indexes = [models.Index(fields=['hebergement', 'statut'])]
        constraints = [
            models.CheckConstraint(check=models.Q(date_fin__gt=models.F('date_debut')), name='alerte_fin_apres_debut'),
        ]

    def __str__(self):
        return f"Alerte {self.email} {self.hebergement_id} {self.date_debut} → {self.date_fin}"
