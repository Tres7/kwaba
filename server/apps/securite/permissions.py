from rest_framework.permissions import IsAuthenticated

ADMIN_API = '/api/v1/admin/'

# Back-office sections an admin can be limited to, shown in this order to the super admins
SECTIONS_ADMIN = {
    'tableau-de-bord': 'Tableau de bord',
    'verifications': 'Vérifications',
    'utilisateurs': 'Utilisateurs',
    'annonces': 'Annonces',
    'reservations': 'Réservations',
    'avis': 'Avis',
    'anti-fraude': 'Anti-fraude',
    'transferts': 'Transferts aéroport',
    'location': 'Location de voiture',
    'experiences': 'Expériences',
    'give': 'Kwa-Ba Give',
    'documents': 'Documents',
    'finances': 'Finances',
    'tarifs': 'Tarifs',
}

# Granted one by one by a super admin, on top of the sections: an admin without limits does not have them (ADR-023)
SPECIAL_PERMISSIONS = {
    'agenda_settings': "Réglages de l'agenda",
    'validate_without_visit': 'Valider une annonce sans visite',
    'activity_log': "Journal d'activité",
}

# Start of the path after /api/v1/admin/ → section. A route listed nowhere is refused to a limited admin
_ROUTES_SECTIONS = {
    'stats/': 'tableau-de-bord',
    'users/': 'utilisateurs',
    'hebergements/': 'annonces',
    'lancement/': 'annonces',
    'reservations/': 'reservations',
    'avis/': 'avis',
    'anti-fraude/': 'anti-fraude',
    'transferts/': 'transferts',
    'location/': 'location',
    'experiences/': 'experiences',
    'give/': 'give',
    'documents/': 'documents',
    'contrats/': 'documents',
    'paiements/finances/': 'finances',
    'paiements/tarifs/': 'tarifs',
    'agenda/': 'verifications',
}
# Open to every admin, whatever their sections
ROUTES_TOUS_ADMINS = ('droits/', 'activity/')


def section_de(chemin: str) -> str | None:
    """Section of a back-office API path, None if it belongs to none."""
    route = chemin.removeprefix(ADMIN_API)
    return next((section for debut, section in _ROUTES_SECTIONS.items() if route.startswith(debut)), None)


def a_acces_section(utilisateur, section: str | None) -> bool:
    """Super admin, admin without limits (admin_sections NULL) or section granted."""
    return utilisateur.is_superuser or utilisateur.admin_sections is None or section in utilisateur.admin_sections


def has_special_permission(user, permission: str) -> bool:
    return user.role == 'admin' and (user.is_superuser or permission in (user.admin_permissions or []))


class EstAdministrateur(IsAuthenticated):
    """Back-office: role and sections read from the database at every request (request.user), never from the frontend
    session."""

    message = "Accès réservé aux administrateurs."

    def has_permission(self, request, view):
        if not (super().has_permission(request, view) and request.user.role == 'admin'):
            return False
        if request.path.removeprefix(ADMIN_API).startswith(ROUTES_TOUS_ADMINS):
            return True
        if a_acces_section(request.user, section_de(request.path)):
            return True
        self.message = "Cette section ne vous est pas ouverte."
        return False
