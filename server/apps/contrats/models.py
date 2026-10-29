import hashlib
import uuid

from django.conf import settings
from django.db import models

from apps.documents.api import stockage_prive

TYPES = [
    ('hote', 'Hôte particulier'),
    ('hotel', 'Hôtel ou résidence hôtelière'),
    ('loueur', 'Propriétaire de véhicule'),
    ('chauffeur', 'Chauffeur partenaire'),
    ('ong', 'ONG partenaire'),
]


def hacher_jeton(jeton: str) -> str:
    """The signature link is never stored in clear: a leak of the table does not allow signing any contract."""
    return hashlib.sha256(jeton.encode()).hexdigest()


class ModeleContratModel(models.Model):
    """Contract template, editable in the back-office.

    The body contains variables {{ partie.nom }}, {{ societe.raison_sociale }}… replaced when issued.
    A paragraph starting with "##" is an article title. Every change increments the version;
    contracts already issued keep the text of their version.
    """
    type = models.CharField(max_length=20, choices=TYPES, unique=True)
    titre = models.CharField(max_length=150)
    corps = models.TextField()
    version = models.PositiveIntegerField(default=1)
    modifie_le = models.DateTimeField(auto_now=True)
    modifie_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        verbose_name = 'Modèle de contrat'
        ordering = ['type']

    def __str__(self):
        return f"{self.get_type_display()} · v{self.version}"


class ContratModel(models.Model):
    """Contract issued to a party (host, rental company, driver, NGO), signed online through a personal link.

    The text is frozen when issued (copy of the template, variables replaced): the party signs exactly what
    they read. The proofs of the signature (timestamp, IP address, browser, SHA-256 fingerprints)
    are kept and printed on the certificate attached to the signed PDF.
    """
    STATUTS = [('a_signer', 'À signer'), ('signe', 'Signé'), ('annule', 'Annulé')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=20, unique=True)
    type = models.CharField(max_length=20, choices=TYPES)
    titre = models.CharField(max_length=150)
    corps = models.TextField(help_text='Texte figé à l\'émission')
    version_modele = models.PositiveIntegerField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='a_signer')

    # Party: only one of these links depending on the type (host and hotel: the host account); its contact details are copied when issued
    hote = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='contrats')
    chauffeur_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    loueur_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    organisation_id = models.UUIDField(null=True, blank=True, db_index=True)
    partie_nom = models.CharField(max_length=150)
    partie_email = models.EmailField()
    partie_telephone = models.CharField(max_length=30, blank=True)

    # Issuing (Kwa-Ba's signature: its legal representative, when issued)
    cree_le = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    kwaba_signataire = models.CharField(max_length=200)
    jeton_hash = models.CharField(max_length=64, unique=True)
    envoye_le = models.DateTimeField(null=True, blank=True)
    expire_le = models.DateTimeField()

    # Party's signature
    signe_le = models.DateTimeField(null=True, blank=True)
    signataire_nom = models.CharField(max_length=150, blank=True)
    signature = models.ImageField(upload_to='contrats/signatures/', storage=stockage_prive, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    methode = models.CharField(max_length=40, blank=True, help_text='lien personnel ou compte Kwa-Ba')
    empreinte_texte = models.CharField(max_length=64, blank=True, help_text='SHA-256 du texte signé')
    empreinte_pdf = models.CharField(max_length=64, blank=True, help_text='SHA-256 du PDF signé')
    pdf = models.FileField(upload_to='contrats/', storage=stockage_prive, blank=True)

    annule_le = models.DateTimeField(null=True, blank=True)
    motif_annulation = models.TextField(blank=True)

    class Meta:
        ordering = ['-cree_le']
        verbose_name = 'Contrat'
        constraints = [
            # A single ongoing contract (to sign or signed) per party
            models.UniqueConstraint(fields=['hote'], condition=~models.Q(statut='annule') & models.Q(hote__isnull=False), name='un_contrat_par_hote'),
            models.UniqueConstraint(fields=['chauffeur_id'], condition=~models.Q(statut='annule') & models.Q(chauffeur_id__isnull=False), name='un_contrat_par_chauffeur'),
            models.UniqueConstraint(fields=['loueur_id'], condition=~models.Q(statut='annule') & models.Q(loueur_id__isnull=False), name='un_contrat_par_loueur'),
            models.UniqueConstraint(fields=['organisation_id'], condition=~models.Q(statut='annule') & models.Q(organisation_id__isnull=False), name='un_contrat_par_ong'),
        ]

    def __str__(self):
        return f"{self.reference} · {self.get_type_display()} · {self.partie_nom}"


class PreinscriptionModel(models.Model):
    """Pre-launch: a host accepted the pre-registration text before creating listings (preinscription.py).

    One row per host and text version, never modified: proof of what was accepted, when and from where.
    """
    hote = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='preinscriptions')
    version = models.PositiveIntegerField()
    langue = models.CharField(max_length=2)
    empreinte_texte = models.CharField(max_length=64, help_text='SHA-256 du texte accepté, dans la langue affichée')
    accepte_le = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = 'contrats_preinscription'
        ordering = ['-accepte_le']
        verbose_name = 'Pré-inscription hôte'
        verbose_name_plural = 'Pré-inscriptions hôtes'
        constraints = [models.UniqueConstraint(fields=['hote', 'version'], name='une_preinscription_par_version')]
