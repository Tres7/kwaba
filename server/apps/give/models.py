import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.paiements.api import PAYS_CHOICES

from .montants import CAUSE_CHOICES

SLUGS_RESERVES = {'don', 'impact'}


class OrganisationModel(models.Model):
    """Partner NGO or association. Visible on the site once verified by the Kwa-Ba team."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=150)
    slug = models.SlugField(max_length=80, unique=True, help_text="Adresse de la page : /give/<slug>")
    cause = models.CharField(max_length=20, choices=CAUSE_CHOICES)
    pays = models.CharField(max_length=2, choices=PAYS_CHOICES)
    ville = models.CharField(max_length=100)
    resume = models.CharField(max_length=200, help_text='Une phrase affichée sur la carte de l\'ONG')
    description = models.TextField(help_text='Mission, actions menées, résultats')
    logo = models.ImageField(upload_to='give/logos/', blank=True)
    image = models.ImageField(upload_to='give/images/', blank=True, help_text='Photo de couverture')
    site_web = models.URLField(blank=True)
    numero_enregistrement = models.CharField(
        max_length=80, help_text="Numéro de récépissé ou d'enregistrement officiel (affiché publiquement)",
    )
    # Verification: the NGO only appears on the site once verified
    verifiee_le = models.DateField(null=True, blank=True, help_text='Date de la vérification ; vide = non publiée')
    verification = models.TextField(
        blank=True, help_text="Ce qui a été vérifié (affiché publiquement) : récépissé, statuts, compte bancaire, visite…",
    )
    # Team only: where and to whom the donations are transferred
    contact_nom = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_telephone = models.CharField(max_length=20, blank=True)
    coordonnees_reversement = models.TextField(
        blank=True, help_text='IBAN / RIB ou compte Mobile Money au nom de l\'ONG (jamais affiché sur le site)',
    )
    actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'give'
        ordering = ['nom']
        verbose_name = 'ONG partenaire'
        verbose_name_plural = 'ONG partenaires'

    def __str__(self):
        return self.nom

    def clean(self):
        # These addresses are already taken by pages of the site (/give/don/…, /give/impact)
        if self.slug in SLUGS_RESERVES:
            raise ValidationError({'slug': "Cette adresse est réservée, choisissez-en une autre."})

    @property
    def publiee(self) -> bool:
        return self.actif and self.verifiee_le is not None


class ProjetModel(models.Model):
    """Specific project of an NGO (a borehole, a school year start…) a donation can be given to."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(OrganisationModel, on_delete=models.CASCADE, related_name='projets')
    titre = models.CharField(max_length=150)
    cause = models.CharField(max_length=20, choices=CAUSE_CHOICES)
    resume = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    lieu = models.CharField(max_length=120, blank=True)
    objectif = models.PositiveIntegerField(null=True, blank=True, help_text='Montant à réunir en FCFA (facultatif)')
    image = models.ImageField(upload_to='give/projets/', blank=True)
    actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'give'
        ordering = ['-cree_le']
        verbose_name = 'Projet'

    def __str__(self):
        return f"{self.titre} ({self.organisation.nom})"


class ReversementModel(models.Model):
    """Transfer to an NGO of a month's donations, with the proof of the transfer."""
    STATUTS = [
        ('a_effectuer', 'À effectuer'),
        ('effectue', 'Effectué'),
    ]
    MOYENS = [
        ('virement', 'Virement bancaire'),
        ('mobile_money', 'Mobile Money'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(OrganisationModel, on_delete=models.PROTECT, related_name='reversements')
    periode = models.DateField(help_text='Premier jour du mois des dons reversés')
    montant = models.PositiveIntegerField(default=0, help_text='Total reversé à l\'ONG en FCFA')
    nb_dons = models.PositiveIntegerField(default=0)
    date_prevue = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='a_effectuer')
    moyen = models.CharField(max_length=20, choices=MOYENS, blank=True)
    reference_operation = models.CharField(max_length=80, blank=True, help_text='Référence du virement')
    justificatif = models.FileField(
        upload_to='give/justificatifs/', blank=True,
        help_text="Preuve du virement (PDF ou image), publiée sur la page de l'ONG : masquer les numéros de compte",
    )
    note = models.TextField(blank=True, help_text="Message public (ce que l'ONG a fait des fonds, par exemple)")
    effectue_le = models.DateField(null=True, blank=True)
    # Emails sent by the worker
    admins_notifies = models.BooleanField(default=False, help_text='Équipe prévenue : reversement à effectuer')
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'give'
        ordering = ['-periode', 'organisation__nom']
        verbose_name = 'Reversement à une ONG'
        verbose_name_plural = 'Reversements aux ONG'
        constraints = [models.UniqueConstraint(fields=['organisation', 'periode'], name='reversement_unique_par_mois')]

    def __str__(self):
        return f"{self.organisation.nom} · {self.periode:%m/%Y} · {self.montant} FCFA ({self.get_statut_display()})"

    @property
    def reference(self):
        return f"REV-{str(self.id)[:6].upper()}"


class DonModel(models.Model):
    STATUTS = [
        ('en_attente', 'En attente de paiement'),
        ('paye', 'Payé'),
        ('echoue', 'Non abouti'),
    ]
    MOYENS = [('mobile_money', 'Mobile Money'), ('carte', 'Carte bancaire'), ('paypal', 'PayPal')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='dons')
    organisation = models.ForeignKey(OrganisationModel, on_delete=models.PROTECT, related_name='dons')
    projet = models.ForeignKey(ProjetModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='dons')
    montant = models.PositiveIntegerField(help_text='Montant choisi par le donateur')
    couvre_frais = models.BooleanField(default=True, help_text='Le donateur ajoute les frais de paiement à son don')
    frais = models.PositiveIntegerField()
    total = models.PositiveIntegerField(help_text='Montant débité')
    montant_ong = models.PositiveIntegerField(help_text="Montant reversé à l'ONG")
    moyen = models.CharField(max_length=20, choices=MOYENS, default='mobile_money')
    partage_identite = models.BooleanField(
        default=False, help_text="Le donateur accepte que son nom et son email soient transmis à l'ONG",
    )
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    paye_le = models.DateTimeField(null=True, blank=True)
    reversement = models.ForeignKey(
        ReversementModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='dons',
    )
    recu_envoye = models.BooleanField(default=False, help_text='Confirmation du don envoyée au donateur')
    reversement_notifie = models.BooleanField(default=False, help_text="Donateur prévenu du reversement à l'ONG")
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'give'
        ordering = ['-cree_le']
        verbose_name = 'Don'

    def __str__(self):
        return f"{self.reference} · {self.montant} FCFA → {self.organisation.nom}"

    @property
    def reference(self):
        return f"DON-{str(self.id)[:6].upper()}"
