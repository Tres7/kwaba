from django.db import models


class CompteurModel(models.Model):
    """Fixed-window counter (attempts, rate limits), incremented atomically by PostgreSQL.

    Django's cache (DatabaseCache) reads then writes in two queries: simultaneous requests all read
    the same value there and get around the limit. See limites.incrementer.
    """
    cle = models.CharField(max_length=200, primary_key=True)
    valeur = models.PositiveIntegerField(default=0)
    expire_le = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'securite_compteur'


class JournalAuditModel(models.Model):
    """Sensitive events: sign-ins, passwords, roles, payout accounts, refused webhooks.

    Never a password, a code nor a token in `details`.
    """
    ACTIONS = [
        ('connexion', 'Connexion'),
        ('connexion_echec', 'Échec de connexion'),
        ('connexion_bloquee', 'Connexion bloquée (trop de tentatives)'),
        ('connexion_google', 'Connexion Google'),
        ('inscription', 'Inscription'),
        ('email_verifie', 'Email vérifié'),
        ('mdp_reinitialise', 'Mot de passe réinitialisé'),
        ('code_bloque', 'Code bloqué (trop de tentatives)'),
        ('role_modifie', 'Rôle modifié'),
        ('compte_desactive', 'Compte désactivé'),
        ('profil_versement_modifie', 'Compte de versement modifié'),
        ('webhook_refuse', 'Webhook refusé'),
        ('admin_connexion_echec', "Échec de connexion à l'administration"),
        ('piece_consultee', "Pièce d'identité consultée"),
        ('annonce_verifiee', 'Annonce validée après visite'),
        ('annonce_refusee', 'Annonce refusée après visite'),
        ('photos_controlees', 'Photos ajoutées contrôlées par un agent'),
        ('position_corrigee', 'Position du logement corrigée par un agent'),
        ('compte_reactive', 'Compte réactivé'),
        ('annonce_modifiee', 'Annonce modifiée par un administrateur'),
        ('annonce_supprimee', 'Annonce supprimée par un administrateur'),
        ('annonce_restauree', 'Annonce restaurée par un administrateur'),
        ('reservation_annulee', 'Réservation annulée par un administrateur'),
        ('avis_supprime', 'Avis supprimé par un administrateur'),
        ('identite_verifiee', "Pièce d'identité validée"),
        ('identite_refusee', "Pièce d'identité refusée"),
        ('backoffice_creation', 'Création depuis le back-office'),
        ('backoffice_modification', 'Modification depuis le back-office'),
        ('backoffice_suppression', 'Suppression depuis le back-office'),
        ('contrat_signe', 'Contrat signé électroniquement'),
        ('candidature_ouverte', 'Candidature hôte ouverte'),
        ('candidature_refusee', 'Candidature hôte refusée'),
        ('roles_hotes_migres', 'Rôles des hôtes existants révisés'),
        ('report_viewed', 'Signalement consulté'),
        ('report_confirmed', 'Signalement confirmé'),
        ('report_rejected', 'Signalement rejeté'),
        ('contest_reviewed', 'Contestation examinée'),
        ('sanction_lifted', 'Sanction levée ou raccourcie'),
        ('legal_hold_changed', 'Conservation prolongée modifiée'),
    ]

    cree_le = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=40, choices=ACTIONS, db_index=True)
    # Id only, without a foreign key: the entry survives the deletion of the account and is never changed
    # (the application role is not allowed to update this log, see deploy/postgres/roles.sql)
    utilisateur_id = models.UUIDField(null=True, blank=True, db_index=True)
    email = models.CharField(max_length=254, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'securite_journal_audit'
        ordering = ['-cree_le']
        verbose_name = "Entrée du journal d'audit"
        verbose_name_plural = "Journal d'audit"

    def __str__(self):
        return f"{self.cree_le:%Y-%m-%d %H:%M} {self.action} {self.email}"


class AlerteFraudeModel(models.Model):
    """Attempt to bypass the platform: contact details or off-site payment offered in a message
    or a listing. Reviewed by an administrator from the back-office (Anti-fraud)."""
    CONTEXTES = [('message', 'Message'), ('annonce', 'Annonce'), ('reservation', 'Réservation')]
    KINDS = [
        ('bypass', 'Contournement'),
        ('refusal', 'Message refusé'),
        ('simulated', 'Refus simulé'),
        ('warning_ignored', 'Envoyé après avertissement'),
        ('false_positive', 'Blocage contesté'),
        ('report', 'Signalement'),
        ('sanction', 'Sanction'),
        ('contest', 'Contestation de sanction'),
        ('abusive_reporter', 'Signaleur abusif'),
    ]

    cree_le = models.DateTimeField(auto_now_add=True, db_index=True)
    utilisateur_id = models.UUIDField(db_index=True)
    contexte = models.CharField(max_length=20, choices=CONTEXTES)
    objet_id = models.CharField(max_length=64, help_text='Conversation, annonce ou réservation concernée')
    types = models.JSONField(default=list, help_text='telephone, email, lien, reseau, application, hors_site')
    # Detected elements (the number, the address…): proof for the administrator, never shown to the other party
    extraits = models.JSONField(default=list)
    masquee = models.BooleanField(default=False, help_text='Des coordonnées ont été masquées')
    kind = models.CharField(max_length=20, choices=KINDS, default='bypass', db_index=True)
    level = models.CharField(max_length=10, blank=True)
    threat_notified_at = models.DateTimeField(null=True, blank=True)
    legal_hold = models.BooleanField(default=False)
    traitee = models.BooleanField(default=False, db_index=True)
    traitee_le = models.DateTimeField(null=True, blank=True)
    traitee_par_id = models.UUIDField(null=True, blank=True, db_index=True)
    note = models.TextField(blank=True)

    class Meta:
        db_table = 'securite_alerte_fraude'
        ordering = ['-cree_le']
        verbose_name = 'Alerte anti-fraude'
        indexes = [models.Index(fields=['utilisateur_id', '-cree_le'], name='alerte_fraude_user_idx')]

    def __str__(self):
        return f"{self.cree_le:%Y-%m-%d} {self.utilisateur_id} {', '.join(self.types)}"
