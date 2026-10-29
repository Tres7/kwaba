"""Car hire, with or without a driver, and driver for the customer's vehicle (mobility offer of
18 October 2026, terms of sale art. 6.5 and 14).

Each vehicle is the listing of a partner owner, entered by the team: the owner sets their price per day and
their deposit (none, one or two days, 100,000 FCFA at most); they stay invisible to the traveller. The driver
(Kwa-Ba partner driver) is charged separately: 7,000 FCFA per day, travel allowances on top. Nothing is offered
until the administration has filled in the settings, at least one vehicle with a price and a place.
"""
import uuid
from functools import cached_property

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.paiements.api import OPERATEUR_CHOICES, PAYS_CHOICES

FUSEAUX = [
    ('Africa/Lome', 'Togo, Ghana, Burkina Faso, Mali, Côte d\'Ivoire, Sénégal (UTC)'),
    ('Africa/Porto-Novo', 'Bénin, Niger, Nigeria (UTC+1)'),
]
CAUTION_MAX = 100_000  # FCFA, deposit cap (terms of sale, art. 14.3)


class ParametresLocationModel(models.Model):
    """Rental rules (a single row): without it, rental is not offered."""
    commission_pourcent = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Commission de Kwa-Ba sur le prix du véhicule, en % (15 % ; 10 % pour un propriétaire fondateur, '
                  '12 % pour un Propriétaire Fidèle)',
    )
    delai_min_jours = models.PositiveSmallIntegerField(
        default=2, validators=[MinValueValidator(1)],
        help_text='Réservation au plus tard N jours avant la prise du véhicule (temps de préparation du propriétaire)',
    )
    duree_max_jours = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)], help_text='Durée maximale d\'une location')
    annulation_gratuite_heures = models.PositiveSmallIntegerField(
        help_text='Remboursement intégral si le voyageur annule au moins N heures avant la prise (48) ; 50 % ensuite '
                  "jusqu'à 24 heures avant, rien après",
    )
    conditions = models.TextField(
        blank=True, help_text='Affiché au voyageur avant de réserver : âge minimum, permis, carburant, kilométrage…',
    )
    caution_en_ligne = models.BooleanField(
        default=True, db_default=True,
        help_text="La caution est payée en ligne avec la location et gardée par Kwa-Ba jusqu'au retour du véhicule "
                  "(sinon, le voyageur la règle au propriétaire à la remise)",
    )
    restitution_caution_heures = models.PositiveSmallIntegerField(
        default=24, db_default=24, validators=[MinValueValidator(1)],
        help_text='Après le retour, délai laissé au propriétaire pour signaler un dommage ; la caution, moins la retenue, '
                  'est ensuite remboursée au voyageur',
    )
    mis_a_jour_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Paramètres de la location'
        verbose_name_plural = 'Paramètres de la location'

    def __str__(self):
        return 'Paramètres de la location'

    def save(self, *args, **kwargs):
        self.pk = 1  # a single row
        super().save(*args, **kwargs)

    @classmethod
    def courants(cls):
        return cls.objects.filter(pk=1).first()


class CategorieVehiculeModel(models.Model):
    """Vehicle offered to the traveller: the listing of a partner owner (their price, deposit, options).

    Historical technical name ("category"): until 22 October 2026, it was a Kwa-Ba fixed-price category.
    """
    GAMMES = [
        ('citadine', 'Citadine'),
        ('berline', 'Berline'),
        ('suv', 'SUV'),
        ('4x4', '4x4 tout-terrain'),
        ('minibus', 'Minibus'),
        ('utilitaire', 'Utilitaire'),
    ]
    BOITES = [('manuelle', 'Manuelle'), ('automatique', 'Automatique')]
    CARBURANTS = [('essence', 'Essence'), ('diesel', 'Diesel'), ('hybride', 'Hybride'), ('electrique', 'Électrique')]
    CAUTIONS = [(0, 'Sans caution'), (1, 'Une journée de location'), (2, 'Deux journées de location')]

    nom = models.CharField(max_length=80, help_text='Par ex. « Toyota RAV4 2019 »')
    gamme = models.CharField(max_length=20, choices=GAMMES, db_index=True)
    exemple_modele = models.CharField(max_length=120, blank=True, help_text='Marque et modèle, par ex. « Toyota RAV4 »')
    description = models.TextField(blank=True)
    places = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    bagages = models.PositiveSmallIntegerField(help_text='Grandes valises')
    boite = models.CharField(max_length=20, choices=BOITES)
    carburant = models.CharField(max_length=20, choices=CARBURANTS, default='essence')
    climatisation = models.BooleanField(default=True)
    proprietaire = models.ForeignKey(
        'PartenaireLocationModel', on_delete=models.PROTECT, null=True, blank=True, related_name='vehicules',
        help_text='Propriétaire partenaire (jamais montré au voyageur)',
    )
    prix_jour = models.PositiveIntegerField(null=True, blank=True, help_text='FCFA par jour, fixé par le propriétaire (sans le chauffeur)')
    sans_chauffeur = models.BooleanField(default=True, db_default=True, help_text='Proposé sans chauffeur (le voyageur conduit)')
    avec_chauffeur = models.BooleanField(default=True, db_default=True, help_text='Proposé avec un chauffeur partenaire (7 000 FCFA par jour en plus)')
    caution_jours = models.PositiveSmallIntegerField(
        choices=CAUTIONS, default=0, db_default=0,
        help_text='Choisie par le propriétaire (sans chauffeur seulement) ; plafonnée à 100 000 FCFA',
    )
    caution = models.PositiveIntegerField(
        default=0, help_text="FCFA, calculée : journées de caution × prix par jour, 100 000 au plus. Payée en ligne et "
                             "gardée par Kwa-Ba jusqu'au retour",
    )
    immatriculation = models.CharField(max_length=20, blank=True, default='', db_default='')
    annee = models.PositiveSmallIntegerField(null=True, blank=True)
    assurance_fin = models.DateField(null=True, blank=True, help_text="Fin de validité de l'assurance : véhicule retiré après")
    visite_technique_fin = models.DateField(null=True, blank=True, help_text='Fin de validité de la visite technique : véhicule retiré après')
    actif = models.BooleanField(default=False, help_text='Proposé aux voyageurs (avec un prix)')
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'places', 'nom']
        verbose_name = 'Véhicule'
        verbose_name_plural = 'Véhicules'

    def __str__(self):
        return f"{self.nom} ({self.get_gamme_display()}, {self.places} places)"

    def save(self, *args, **kwargs):
        self.caution = min(self.caution_jours * (self.prix_jour or 0), CAUTION_MAX)
        super().save(*args, **kwargs)

    def propose(self, formule: str) -> bool:
        return bool(self.prix_jour) and (self.avec_chauffeur if formule == 'avec_chauffeur' else self.sans_chauffeur)


class PhotoVehiculeModel(models.Model):
    """Photos of a vehicle; the first one (lowest order) is the main photo."""
    MAX_PAR_CATEGORIE = 10

    categorie = models.ForeignKey(CategorieVehiculeModel, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='locations/')
    ordre = models.PositiveSmallIntegerField(default=0)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre', 'id']
        verbose_name = 'Photo de véhicule'
        verbose_name_plural = 'Photos de véhicules'

    def __str__(self):
        return f"{self.categorie.nom} · photo {self.ordre + 1}"


class LieuRemiseModel(models.Model):
    """Where the vehicle (or the driver) is handed over and returned: airport, agency, or delivery to the traveller's address."""
    nom = models.CharField(max_length=120, help_text='Par ex. « Aéroport de Lomé » ou « Livraison à votre adresse, Lomé »')
    ville = models.CharField(max_length=100)
    fuseau = models.CharField(max_length=40, choices=FUSEAUX, help_text='Heure locale des réservations')
    adresse_requise = models.BooleanField(default=False, help_text='Le voyageur indique une adresse (livraison)')
    frais = models.PositiveIntegerField(default=0, help_text='FCFA ajoutés à la location, à la remise et au retour')
    actif = models.BooleanField(default=True)
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ville', 'ordre', 'nom']
        verbose_name = 'Lieu de remise'
        verbose_name_plural = 'Lieux de remise'

    def __str__(self):
        return f"{self.nom} ({self.ville})"


class PartenaireLocationModel(models.Model):
    """Partner vehicle owner (individual or agency), paid by Mobile Money after each rental, minus the commission:
    15 %, 10 % during the Founders Programme, 12 % with the Loyal Owner status."""
    nom = models.CharField(max_length=120, help_text="Nom du propriétaire ou de l'agence")
    contact = models.CharField(max_length=120, help_text='Personne à contacter')
    telephone = models.CharField(max_length=20, help_text="Avec l'indicatif, par ex. +228 90 00 00 00")
    email = models.EmailField(blank=True, help_text='Facultatif : reçoit le détail des locations attribuées')
    categories = models.ManyToManyField(CategorieVehiculeModel, related_name='partenaires', blank=True,
                                        help_text='Ancien catalogue : véhicules sans propriétaire que ce partenaire peut fournir')
    lieux = models.ManyToManyField(LieuRemiseModel, related_name='partenaires', help_text='Lieux où il remet ses véhicules')
    actif = models.BooleanField(default=True)
    fondateur_debut = models.DateField(null=True, blank=True, help_text='Programme Fondateurs (20 premiers) : premier jour à 10 %')
    fondateur_fin = models.DateField(null=True, blank=True, help_text='Programme Fondateurs : dernier jour à 10 % (6 mois)')
    pays_versement = models.CharField(max_length=2, choices=PAYS_CHOICES)
    operateur_versement = models.CharField(max_length=30, choices=OPERATEUR_CHOICES)
    numero_versement = models.CharField(max_length=15, help_text="Sans l'indicatif")
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom']
        verbose_name = 'Propriétaire de véhicules'
        verbose_name_plural = 'Propriétaires de véhicules'

    def __str__(self):
        return self.nom


class LocationModel(models.Model):
    STATUTS = [
        ('en_attente_paiement', 'En attente de paiement'),
        ('confirmee', 'Payée, à attribuer'),
        ('partenaire_assigne', 'Attribuée'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    FORMULES = [('sans_chauffeur', 'Voiture seule'), ('avec_chauffeur', 'Avec chauffeur'),
                ('chauffeur_seul', 'Chauffeur pour votre véhicule')]
    ANNULEE_PAR = [('voyageur', 'Voyageur'), ('plateforme', 'Kwa-Ba'), ('expiration', 'Paiement non effectué à temps')]
    MOYENS = [('mobile_money', 'Mobile Money'), ('carte', 'Carte bancaire'), ('paypal', 'PayPal')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    voyageur_id = models.UUIDField(db_index=True)
    reservation_id = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text='Séjour Kwa-Ba associé (facultatif) : avec un chauffeur, Pack Séjour (frais du logement à 3 %)',
    )
    categorie = models.ForeignKey(CategorieVehiculeModel, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name='locations', help_text='Véhicule ; vide pour un chauffeur seul')
    formule = models.CharField(max_length=20, choices=FORMULES)
    lieu_prise = models.ForeignKey(LieuRemiseModel, on_delete=models.PROTECT, related_name='+')
    adresse_prise = models.CharField(max_length=255, blank=True)
    lieu_retour = models.ForeignKey(LieuRemiseModel, on_delete=models.PROTECT, related_name='+')
    adresse_retour = models.CharField(max_length=255, blank=True)
    debut = models.DateTimeField(help_text='Prise du véhicule (ou début de la mission)')
    fin = models.DateTimeField(help_text='Retour du véhicule (ou fin de la mission)')
    passagers = models.PositiveSmallIntegerField()
    telephone = models.CharField(max_length=20, help_text='Numéro du voyageur (WhatsApp)')
    precisions = models.TextField(help_text='Ce que le voyageur veut : trajets prévus, siège enfant, horaires…')
    # Car only: the driver
    conducteur = models.CharField(max_length=120, blank=True)
    permis_numero = models.CharField(max_length=40, blank=True)
    permis_pays = models.CharField(max_length=60, blank=True)
    # With a driver: days outside Lomé (travel allowances) and driver asked for again ("My driver")
    jours_hors_lome = models.PositiveSmallIntegerField(default=0, db_default=0, help_text='Jours dans le pays hors de Lomé')
    jours_hors_pays = models.PositiveSmallIntegerField(default=0, db_default=0)
    chauffeur_demande_id = models.BigIntegerField(
        null=True, blank=True, db_index=True, help_text='« Mon chauffeur » : chauffeur que le voyageur redemande',
    )

    # Prices frozen at booking (rates may change afterwards). prix = vehicle + places + driver + allowances
    jours = models.PositiveSmallIntegerField()
    prix_jour = models.PositiveIntegerField(help_text='Prix du véhicule par jour (0 pour un chauffeur seul)')
    frais_lieux = models.PositiveIntegerField()
    prix_chauffeur = models.PositiveIntegerField(default=0, db_default=0, help_text='7 000 FCFA par jour')
    primes = models.PositiveIntegerField(default=0, db_default=0, help_text='Primes de déplacement, reversées au chauffeur')
    prix = models.PositiveIntegerField(help_text='Total payé par le voyageur (hors caution)')
    commission = models.PositiveIntegerField(help_text='Commission de Kwa-Ba sur le prix du véhicule (payée par le propriétaire)')
    part_kwaba_chauffeur = models.PositiveIntegerField(default=0, db_default=0, help_text='1 000 FCFA par jour, 500 en Excellence ou en « Mon chauffeur »')
    caution = models.PositiveIntegerField(default=0)
    # Deposit paid online with the rental (frozen at booking): Kwa-Ba keeps it until the return, then refunds it
    # to the traveller minus the withheld amount (damage reported by the owner, paid to them). Otherwise, paid to
    # the owner at the vehicle handover (rentals booked before the online deposit).
    caution_en_ligne = models.BooleanField(default=False, db_default=False)
    caution_retenue = models.PositiveIntegerField(default=0, db_default=0, help_text='Gardée sur la caution et versée au propriétaire')
    caution_motif = models.CharField(max_length=255, blank=True, default='', db_default='', help_text='Motif de la retenue')
    caution_restituee_le = models.DateTimeField(null=True, blank=True, help_text='Remboursement de la caution prévu')
    moyen = models.CharField(max_length=20, choices=MOYENS, default='mobile_money')

    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente_paiement')
    expire_le = models.DateTimeField(null=True, blank=True)
    # Pending payment emails: 0 none, 1 "to pay before", 2 reminder sent, 3 cancellation notified
    relance_paiement = models.PositiveSmallIntegerField(default=0, editable=False)
    annulee_par = models.CharField(max_length=20, choices=ANNULEE_PAR, blank=True)
    annulee_le = models.DateTimeField(null=True, blank=True)
    # Assigned by the team
    partenaire = models.ForeignKey(PartenaireLocationModel, on_delete=models.PROTECT, null=True, blank=True, related_name='locations')
    chauffeur_partenaire_id = models.BigIntegerField(
        null=True, blank=True, db_index=True, help_text='Chauffeur partenaire de Kwa-Ba (formules avec chauffeur)',
    )
    vehicule = models.CharField(max_length=120, blank=True, help_text='Marque, modèle et couleur du véhicule remis')
    immatriculation = models.CharField(max_length=20, blank=True)
    chauffeur_nom = models.CharField(max_length=120, blank=True, help_text='Formule avec chauffeur')
    chauffeur_telephone = models.CharField(max_length=20, blank=True)
    # Emails sent by the worker (one flag per email: a failed sending is retried, never doubled)
    confirmation_notifiee = models.BooleanField(default=False)
    admins_notifies = models.BooleanField(default=False)
    alerte_sans_partenaire = models.BooleanField(default=False)
    partenaire_notifie = models.BooleanField(default=False, help_text='Coordonnées du propriétaire et du chauffeur envoyées au voyageur')
    location_envoyee_partenaire = models.BooleanField(default=False)
    mission_envoyee_chauffeur = models.BooleanField(default=False, db_default=False, help_text='Détail de la mission envoyé au chauffeur')
    caution_notifiee = models.BooleanField(default=False, db_default=False, help_text='Restitution de la caution annoncée au voyageur')
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-debut']
        verbose_name = 'Location de voiture'
        verbose_name_plural = 'Locations de voitures'

    def __str__(self):
        return f"{self.reference} · {self.libelle}, {self.lieu_prise.ville}"

    @cached_property
    def voyageur(self):
        from apps.users.api import compte
        return compte(self.voyageur_id)

    @property
    def reference(self):
        return f"LOC-{str(self.id)[:6].upper()}"

    @property
    def libelle(self) -> str:
        return self.categorie.nom if self.categorie_id else 'Chauffeur pour votre véhicule'

    @property
    def avec_chauffeur(self) -> bool:
        return self.formule in ('avec_chauffeur', 'chauffeur_seul')

    @property
    def caution_gardee(self) -> int:
        """Deposit Kwa-Ba collects with the rental (0 if it is paid to the owner)."""
        return self.caution if self.caution_en_ligne else 0

    @property
    def montant_a_payer(self) -> int:
        """What the traveller pays online: the rental and, where applicable, the deposit."""
        return self.prix + self.caution_gardee

    @property
    def part_proprietaire(self) -> int:
        """What goes to the owner before commission: vehicle and handover fees."""
        return self.prix - self.prix_chauffeur - self.primes

    @property
    def montant_partenaire(self):
        return self.part_proprietaire - self.commission

    @property
    def montant_chauffeur(self) -> int:
        return self.prix_chauffeur + self.primes - self.part_kwaba_chauffeur


class _VersementMixin(models.Model):
    """Payment of a partner after the rental (same rules as the payouts to the transfer drivers)."""
    STATUTS = [('planifie', 'Planifié'), ('en_cours', 'En cours'), ('envoye', 'Envoyé'), ('echoue', 'Échoué'), ('annule', 'Annulé')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
        abstract = True
        ordering = ['date_prevue']


class VersementPartenaireModel(_VersementMixin):
    """Owner's payment: vehicle price and handover fees (plus the amount withheld from the deposit), minus the commission."""
    location = models.OneToOneField(LocationModel, on_delete=models.PROTECT, related_name='versement')
    partenaire = models.ForeignKey(PartenaireLocationModel, on_delete=models.PROTECT, related_name='versements')

    class Meta(_VersementMixin.Meta):
        verbose_name = 'Versement à un propriétaire'
        verbose_name_plural = 'Versements aux propriétaires'

    def __str__(self):
        return f"{self.montant} FCFA → {self.partenaire} ({self.get_statut_display()})"


class VersementChauffeurLocationModel(_VersementMixin):
    """Partner driver's payment: 6,000 FCFA per day (6,500 for Excellence or "My driver") and allowances."""
    location = models.OneToOneField(LocationModel, on_delete=models.PROTECT, related_name='versement_chauffeur')
    chauffeur_id = models.BigIntegerField(db_index=True)

    class Meta(_VersementMixin.Meta):
        verbose_name = "Versement à un chauffeur (location)"
        verbose_name_plural = 'Versements aux chauffeurs (locations)'

    def __str__(self):
        return f"{self.montant} FCFA → chauffeur {self.chauffeur_id} ({self.get_statut_display()})"
