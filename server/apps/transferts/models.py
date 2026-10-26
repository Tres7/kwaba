import uuid

from django.conf import settings
from django.db import models

from apps.paiements.operateurs import OPERATEUR_CHOICES, PAYS_CHOICES

from .tarifs import CATEGORIE_CHOICES


class AeroportModel(models.Model):
    code = models.CharField(max_length=3, primary_key=True, help_text='Code IATA, par ex. LFW')
    nom = models.CharField(max_length=120)
    ville = models.CharField(max_length=100)
    pays = models.CharField(max_length=2)
    fuseau = models.CharField(max_length=40, help_text='Fuseau horaire, par ex. Africa/Lome')
    actif = models.BooleanField(default=True)

    class Meta:
        app_label = 'transferts'
        ordering = ['ville']
        verbose_name = 'Aéroport'

    def __str__(self):
        return f"{self.ville} · {self.nom} ({self.code})"


class TarifTransfertModel(models.Model):
    """Base price of a transfer from the airport to the city, per vehicle category."""
    aeroport = models.ForeignKey(AeroportModel, on_delete=models.CASCADE, related_name='tarifs')
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES)
    prix = models.PositiveIntegerField(help_text='En FCFA, hors majoration de nuit')
    actif = models.BooleanField(default=True)

    class Meta:
        app_label = 'transferts'
        verbose_name = 'Tarif'
        constraints = [models.UniqueConstraint(fields=['aeroport', 'categorie'], name='tarif_unique_par_categorie')]

    def __str__(self):
        return f"{self.aeroport_id} · {self.get_categorie_display()} : {self.prix} FCFA"


class ChauffeurModel(models.Model):
    """Partner driver (self-employed), paid by Mobile Money after each ride or mission (driver contract):
    transfers with their vehicle, and day missions (an owner's car, the customer's vehicle)."""
    prenom = models.CharField(max_length=60)
    nom = models.CharField(max_length=60)
    telephone = models.CharField(max_length=20, help_text='Avec l\'indicatif, par ex. +228 90 00 00 00')
    email = models.EmailField(blank=True, help_text='Facultatif : reçoit le détail des courses attribuées')
    aeroports = models.ManyToManyField(AeroportModel, related_name='chauffeurs')
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES)
    vehicule = models.CharField(max_length=120, help_text='Marque, modèle et couleur')
    immatriculation = models.CharField(max_length=20)
    actif = models.BooleanField(default=True)
    excellence = models.BooleanField(
        default=False, db_default=False,
        help_text='Statut « Chauffeur Excellence » (revu chaque trimestre) : 6 500 FCFA par jour au lieu de 6 000',
    )
    # Mobile Money account for their payouts
    pays_versement = models.CharField(max_length=2, choices=PAYS_CHOICES)
    operateur_versement = models.CharField(max_length=30, choices=OPERATEUR_CHOICES)
    numero_versement = models.CharField(max_length=15, help_text='Sans l\'indicatif')
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'transferts'
        ordering = ['prenom', 'nom']
        verbose_name = 'Chauffeur partenaire'
        verbose_name_plural = 'Chauffeurs partenaires'

    def __str__(self):
        return f"{self.prenom} {self.nom} · {self.vehicule} ({self.get_categorie_display()})"


class TransfertModel(models.Model):
    STATUTS = [
        ('en_attente_paiement', 'En attente de paiement'),
        ('confirme', 'Payé, chauffeur à attribuer'),
        ('chauffeur_assigne', 'Chauffeur attribué'),
        ('termine', 'Effectué'),
        ('annule', 'Annulé'),
    ]
    ANNULE_PAR = [
        ('voyageur', 'Voyageur'),
        ('plateforme', 'Kwa-Ba'),
        ('expiration', 'Paiement non effectué à temps'),
    ]
    MOYENS = [('mobile_money', 'Mobile Money'), ('carte', 'Carte bancaire'), ('paypal', 'PayPal')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    voyageur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='transferts')
    reservation = models.ForeignKey(
        'reservations.ReservationModel', on_delete=models.SET_NULL, null=True, blank=True, related_name='transferts',
        help_text='Séjour Kwa-Ba associé (facultatif)',
    )
    aeroport = models.ForeignKey(AeroportModel, on_delete=models.PROTECT, related_name='transferts')
    arrivee = models.DateTimeField(help_text="Heure d'atterrissage prévue")
    numero_vol = models.CharField(max_length=10)
    passagers = models.PositiveSmallIntegerField()
    bagages = models.PositiveSmallIntegerField()
    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES)
    destination = models.CharField(max_length=255, help_text='Adresse de dépose')
    telephone = models.CharField(max_length=20, help_text='Numéro du voyageur, joignable à l\'arrivée (WhatsApp)')
    message = models.TextField(blank=True)

    prix = models.PositiveIntegerField()
    commission = models.PositiveIntegerField()
    majoration_nuit = models.BooleanField(default=False)
    moyen = models.CharField(max_length=20, choices=MOYENS, default='mobile_money')

    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente_paiement')
    expire_le = models.DateTimeField(null=True, blank=True)
    # Pending payment emails: 0 none, 1 "to pay before", 2 reminder sent, 3 cancellation notified
    relance_paiement = models.PositiveSmallIntegerField(default=0, editable=False)
    annule_par = models.CharField(max_length=20, choices=ANNULE_PAR, blank=True)
    annule_le = models.DateTimeField(null=True, blank=True)
    chauffeur = models.ForeignKey(ChauffeurModel, on_delete=models.PROTECT, null=True, blank=True, related_name='transferts')
    # Emails sent by the worker (one flag per email: a failed sending is retried, never doubled)
    confirmation_notifiee = models.BooleanField(default=False, help_text='Paiement confirmé au voyageur')
    admins_notifies = models.BooleanField(default=False, help_text='Administrateurs prévenus : chauffeur à attribuer')
    alerte_sans_chauffeur = models.BooleanField(default=False, help_text='Alerte : arrivée dans moins de 24 h sans chauffeur')
    chauffeur_notifie = models.BooleanField(default=False, help_text='Coordonnées du chauffeur envoyées au voyageur')
    course_envoyee_chauffeur = models.BooleanField(default=False, help_text='Détail de la course envoyé au chauffeur')
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'transferts'
        ordering = ['-arrivee']
        verbose_name = 'Transfert aéroport'
        verbose_name_plural = 'Transferts aéroport'

    def __str__(self):
        return f"{self.reference} · {self.aeroport_id} → {self.destination[:40]}"

    @property
    def reference(self):
        return f"TRF-{str(self.id)[:6].upper()}"

    @property
    def montant_chauffeur(self):
        return self.prix - self.commission


class VersementChauffeurModel(models.Model):
    """Payment of the driver after the ride (same rules as the payouts to hosts)."""
    STATUTS = [
        ('planifie', 'Planifié'),
        ('en_cours', 'En cours'),
        ('envoye', 'Envoyé'),
        ('echoue', 'Échoué'),
        ('annule', 'Annulé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfert = models.OneToOneField(TransfertModel, on_delete=models.PROTECT, related_name='versement')
    chauffeur = models.ForeignKey(ChauffeurModel, on_delete=models.PROTECT, related_name='versements')
    montant_brut = models.PositiveIntegerField()
    commission = models.PositiveIntegerField()
    montant = models.PositiveIntegerField()
    date_prevue = models.DateTimeField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='planifie')
    payout_id = models.CharField(max_length=64, blank=True)
    mode = models.CharField(max_length=30, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    tentatives = models.PositiveSmallIntegerField(default=0)
    derniere_erreur = models.TextField(blank=True)
    envoye_le = models.DateTimeField(null=True, blank=True)
    notifie = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'transferts'
        ordering = ['date_prevue']
        verbose_name = 'Versement à un chauffeur'
        verbose_name_plural = 'Versements aux chauffeurs'

    def __str__(self):
        return f"{self.montant} FCFA → {self.chauffeur} ({self.get_statut_display()})"
