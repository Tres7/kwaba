import uuid

from django.conf import settings
from django.db import models

from .operateurs import OPERATEUR_CHOICES, PAYS_CHOICES


class ProfilVersementModel(models.Model):
    """Where the host receives their money."""
    hote = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profil_versement')
    pays = models.CharField(max_length=2, choices=PAYS_CHOICES)
    operateur = models.CharField(max_length=30, choices=OPERATEUR_CHOICES)
    numero = models.CharField(max_length=15, help_text="Numéro local, sans l'indicatif du pays")
    titulaire = models.CharField(max_length=120, help_text='Nom du titulaire du compte Mobile Money')
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'paiements'
        verbose_name = 'Profil de versement'
        verbose_name_plural = 'Profils de versement'

    def __str__(self):
        return f"{self.hote.email} · {self.get_operateur_display()} {self.numero}"


class ConditionsHoteModel(models.Model):
    """Host's commission, set by the team: individual host (8 %), hotel or serviced residence (12 %), and
    Founders Programme (5 % between two dates, first 50 individual hosts). Without a row: individual host."""
    CATEGORIES = [('particulier', 'Hôte particulier'), ('hotel', 'Hôtel ou résidence hôtelière')]

    hote = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conditions_hote')
    categorie = models.CharField(max_length=20, choices=CATEGORIES, default='particulier')
    fondateur_debut = models.DateField(null=True, blank=True, help_text='Programme Fondateurs : premier jour à 5 %')
    fondateur_fin = models.DateField(null=True, blank=True, help_text='Programme Fondateurs : dernier jour à 5 % (6 mois)')
    mis_a_jour_le = models.DateTimeField(auto_now=True)
    mis_a_jour_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        app_label = 'paiements'
        verbose_name = "Conditions d'un hôte"
        verbose_name_plural = 'Conditions des hôtes'

    def __str__(self):
        return f"{self.hote.email} · {self.get_categorie_display()}"

    def fondateur_le(self, jour) -> bool:
        return bool(self.categorie == 'particulier' and self.fondateur_debut and self.fondateur_fin
                    and self.fondateur_debut <= jour <= self.fondateur_fin)


class ObjetPayeMixin:
    """What is paid: a listing booking, an airport transfer, a car rental or a donation, described by its module
    (paiements.registre)."""
    TYPES_OBJETS = ('reservation', 'transfert', 'location', 'don')

    @property
    def type_objet(self) -> str:
        return next(t for t in self.TYPES_OBJETS if getattr(self, f'{t}_id', None))

    @property
    def objet_id(self):
        return getattr(self, f'{self.type_objet}_id')

    @property
    def description(self) -> dict:
        from .registre import PRODUITS

        if not hasattr(self, '_description'):
            self._description = PRODUITS[self.type_objet].decrire(self.objet_id)
        return self._description

    @property
    def payeur(self):
        return self.description['payeur']

    @property
    def reference(self):
        return self.description['reference']

    @property
    def libelle(self):
        return self.description['libelle']


class PaiementModel(ObjetPayeMixin, models.Model):
    """A collection attempt (the same object may have several: failure then new try)."""
    PRESTATAIRES = [
        ('fedapay', 'FedaPay (Mobile Money, carte)'),
        ('paypal', 'PayPal'),
    ]
    STATUTS = [
        ('en_attente', 'En attente'),
        ('reussi', 'Réussi'),
        ('echoue', 'Échoué'),
        ('annule', 'Annulé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # The paid object, by id (the modules of the products keep their objects): exactly one is filled
    reservation_id = models.UUIDField(null=True, blank=True, db_index=True)
    transfert_id = models.UUIDField(null=True, blank=True, db_index=True)
    don_id = models.UUIDField(null=True, blank=True, db_index=True)
    location_id = models.UUIDField(null=True, blank=True, db_index=True)
    montant = models.PositiveIntegerField()
    devise = models.CharField(max_length=3, default='XOF')
    prestataire = models.CharField(max_length=20, choices=PRESTATAIRES, default='fedapay')
    # Id at the provider: FedaPay transaction or PayPal order
    transaction_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    # PayPal: amount actually charged in euros, and capture id (used for refunds)
    montant_eur = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    capture_id = models.CharField(max_length=64, blank=True)
    url_paiement = models.URLField(max_length=500, blank=True)
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    # Method used and number charged, returned by FedaPay: used for refunds
    mode = models.CharField(max_length=40, blank=True)
    telephone = models.CharField(max_length=20, blank=True)
    pays_telephone = models.CharField(max_length=2, blank=True)
    # Confirmation emails sent by the worker (one flag per recipient: no duplicate if one fails)
    notifie = models.BooleanField(default=False)
    notifie_hote = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'paiements'
        ordering = ['-cree_le']
        verbose_name = 'Paiement'
        # Exactly one paid object
        constraints = [models.CheckConstraint(
            condition=models.Q(reservation_id__isnull=False, transfert_id__isnull=True, don_id__isnull=True, location_id__isnull=True)
            | models.Q(reservation_id__isnull=True, transfert_id__isnull=False, don_id__isnull=True, location_id__isnull=True)
            | models.Q(reservation_id__isnull=True, transfert_id__isnull=True, don_id__isnull=False, location_id__isnull=True)
            | models.Q(reservation_id__isnull=True, transfert_id__isnull=True, don_id__isnull=True, location_id__isnull=False),
            name='paiement_un_seul_objet',
        )]

    def __str__(self):
        return f"{self.montant} FCFA · {self.get_statut_display()} · {self.reference}"


class VersementModel(models.Model):
    """Payout of the host's share, triggered after the traveller's arrival."""
    STATUTS = [
        ('planifie', 'Planifié'),
        ('en_cours', 'En cours'),
        ('envoye', 'Envoyé'),
        ('echoue', 'Échoué'),
        ('annule', 'Annulé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation_id = models.UUIDField(unique=True)
    hote = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='versements')
    montant_brut = models.PositiveIntegerField(help_text='Prix des nuits revenant à l\'hôte, avant commission')
    commission = models.PositiveIntegerField()
    montant = models.PositiveIntegerField(help_text='Montant versé à l\'hôte')
    devise = models.CharField(max_length=3, default='XOF')
    date_prevue = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='planifie')
    payout_id = models.CharField(max_length=64, blank=True)
    mode = models.CharField(max_length=30, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    tentatives = models.PositiveSmallIntegerField(default=0)
    derniere_erreur = models.TextField(blank=True)
    envoye_le = models.DateTimeField(null=True, blank=True)
    # Email sent for the final state (paid to the host, or failure reported to the administrators)
    notifie = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'paiements'
        ordering = ['date_prevue']
        verbose_name = 'Versement à un hôte'
        verbose_name_plural = 'Versements aux hôtes'

    def __str__(self):
        return f"{self.montant} FCFA → {self.hote.email} ({self.get_statut_display()})"


class RemboursementModel(ObjetPayeMixin, models.Model):
    STATUTS = [
        ('attente_numero', 'En attente du numéro du voyageur'),
        ('a_envoyer', 'À envoyer'),
        ('en_cours', 'En cours'),
        ('envoye', 'Envoyé'),
        ('a_traiter', 'À traiter manuellement'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation_id = models.UUIDField(null=True, blank=True, db_index=True)
    transfert_id = models.UUIDField(null=True, blank=True, db_index=True)
    location_id = models.UUIDField(null=True, blank=True, db_index=True)
    paiement = models.ForeignKey(PaiementModel, on_delete=models.PROTECT, related_name='remboursements')
    montant = models.PositiveIntegerField()
    devise = models.CharField(max_length=3, default='XOF')
    motif = models.CharField(max_length=255)
    statut = models.CharField(max_length=20, choices=STATUTS, default='a_envoyer')
    # Mobile Money account given by the traveller (FedaPay does not give the charged number)
    pays = models.CharField(max_length=2, blank=True, choices=PAYS_CHOICES)
    operateur = models.CharField(max_length=30, blank=True, choices=OPERATEUR_CHOICES)
    numero = models.CharField(max_length=15, blank=True)
    payout_id = models.CharField(max_length=64, blank=True)
    tentatives = models.PositiveSmallIntegerField(default=0)
    derniere_erreur = models.TextField(blank=True)
    envoye_le = models.DateTimeField(null=True, blank=True)
    # Email sent for the final state (refunded, or manual handling reported to the administrators)
    notifie = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'paiements'
        ordering = ['-cree_le']
        verbose_name = 'Remboursement'

    def __str__(self):
        return f"{self.montant} FCFA · {self.reference} ({self.get_statut_display()})"
