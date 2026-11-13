import uuid
from functools import cached_property

from django.db import models



class ReservationModel(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente de paiement'),
        ('confirmed', 'Confirmée'),
        ('cancelled', 'Annulée'),
    ]

    PAYMENT_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('carte', 'Carte bancaire'),
        ('paypal', 'PayPal'),
    ]

    ANNULE_PAR_CHOICES = [
        ('voyageur', 'Voyageur'),
        ('hote', 'Hôte'),
        ('plateforme', 'Kwa-Ba'),
        ('expiration', 'Paiement non effectué à temps'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hebergement_id = models.UUIDField(db_index=True)
    # Unit type booked and number of identical units (a hotel room type, or the single type of a house).
    # Filled for every booking (data migration); a type with bookings is deactivated, never deleted.
    type_logement_id = models.UUIDField(null=True, blank=True, db_index=True)
    nb_unites = models.PositiveSmallIntegerField(default=1, db_default=1)
    guest_id = models.UUIDField(db_index=True)
    check_in = models.DateField()
    check_out = models.DateField()
    guests_count = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    # Never confirmed by default: only a payment (or the offline mode in development) confirms a booking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='mobile_money')
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Amounts frozen at booking, as whole FCFA (see apps/paiements/tarifs.py).
    # Zero for the bookings created before online payment.
    prix_nuits = models.PositiveIntegerField(null=True, blank=True)
    frais_service = models.PositiveIntegerField(null=True, blank=True)
    commission_hote = models.PositiveIntegerField(null=True, blank=True)
    # Cleaning fee of the listing type at booking time, for the host in full (null before it existed)
    frais_menage = models.PositiveIntegerField(null=True, blank=True)

    # Stay terms frozen at booking, as the traveller accepted them: the host may change the listing afterwards.
    # The bookings made before were given the listing's values of the day (migration 0010).
    politique_annulation = models.CharField(max_length=10, blank=True, default='', db_default='')
    # Ledger (finance): when the commission became Kwa-Ba's revenue, at the arrival. Set on the existing bookings by
    # the migration that added it: their payments are older than the ledger
    commission_constatee_le = models.DateTimeField(null=True, blank=True)
    arrivee_a_partir = models.TimeField(null=True, blank=True)
    depart_avant = models.TimeField(null=True, blank=True)
    petit_dejeuner = models.CharField(max_length=10, blank=True, default='', db_default='')
    petit_dejeuner_prix = models.PositiveIntegerField(null=True, blank=True)

    # Booking waiting for payment: the dates are held until this deadline
    expire_le = models.DateTimeField(null=True, blank=True)
    annule_par = models.CharField(max_length=20, blank=True, choices=ANNULE_PAR_CHOICES)
    annule_le = models.DateTimeField(null=True, blank=True)
    # Pending payment emails: 0 none, 1 "to pay before", 2 reminder sent, 3 cancellation notified
    relance_paiement = models.PositiveSmallIntegerField(default=0, editable=False)

    class Meta:
        app_label = 'reservations'
        ordering = ['-created_at']

    def __str__(self):
        return f"RES-{str(self.id)[:8].upper()} · {self.hebergement_id}"

    @cached_property
    def guest(self):
        from apps.users.api import compte
        return compte(self.guest_id)

    @property
    def nights(self):
        return (self.check_out - self.check_in).days

    @property
    def montant_hote(self):
        if self.prix_nuits is None or self.commission_hote is None:
            return None
        return self.prix_nuits - self.commission_hote + (self.frais_menage or 0)

    @property
    def reference(self):
        return f"RES-AF{self.created_at.year}-{str(self.id)[:4].upper()}"


class DemandePaiementModel(models.Model):
    """The traveller asks someone else to pay their booking in full (payment by a third party).

    A secret link, valid 24 hours, that the traveller sends to whoever they want, and that can also be opened to the
    members of a Together trip the booking is shared with. Only the fingerprint of the link is kept: like a password,
    it cannot be read again, a new link replaces the previous one. One request at a time per booking.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation = models.ForeignKey(ReservationModel, on_delete=models.CASCADE, related_name='demandes_paiement')
    empreinte_jeton = models.CharField(max_length=64, unique=True, help_text='SHA-256 du lien secret')
    # Together trip whose members may pay without the link (the booking is shared with it)
    voyage_id = models.UUIDField(null=True, blank=True, db_index=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    expire_le = models.DateTimeField()
    revoquee_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'reservations'
        ordering = ['-cree_le']
        verbose_name = 'Demande de paiement par un tiers'
        verbose_name_plural = 'Demandes de paiement par un tiers'

    def __str__(self):
        return f"Paiement par un tiers · {self.reservation.reference}"
