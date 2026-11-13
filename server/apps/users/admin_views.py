"""Back-office: user accounts (list, role, deactivation, host commission, admin rights).
Contract: documentation/modules/backoffice-api.md."""
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.response import Response

from apps.hebergements import api as hebergements
from apps.paiements import api as paiements
from apps.reservations import api as reservations
from apps.activity import api as activity
from apps.securite.backoffice import VueAdmin, booleen as _booleen, introuvable as _introuvable, paginer as _paginer
from apps.securite.permissions import SECTIONS_ADMIN, SPECIAL_PERMISSIONS

from .api import ROLES, hote_ou_candidat, revoquer_jetons
from .infrastructure.persistence.models import UserModel

MIN_MOTIF = 10  # characters, like the refusal of a listing


def _conditions(u) -> dict | None:
    """Host's commission: category, Founders Programme and rate applied today."""
    return paiements.conditions_commission(u) if hote_ou_candidat(u) else None


def _modifier_candidature(request, cible, valeur, motif) -> str | None:
    """Refuses an ongoing candidature, or reopens a refused one. Returns an error message, or None."""
    motif = str(motif or '').strip()
    if valeur == 'refusee' and cible.candidature_hote == 'ouverte':
        if len(motif) < MIN_MOTIF:
            return f"Expliquez le motif du refus ({MIN_MOTIF} caractères au moins)."
        cible.candidature_hote, cible.candidature_motif = 'refusee', motif
        activity.record('candidature_refusee', request, actor=request.user, cible_id=str(cible.pk), motif=motif)
    elif valeur == 'ouverte' and cible.candidature_hote == 'refusee':
        cible.candidature_hote, cible.candidature_motif = 'ouverte', ''
        activity.record('candidature_ouverte', request, actor=request.user, cible_id=str(cible.pk))
    else:
        return "Cette candidature ne peut pas être modifiée ainsi."
    return None


def _utilisateurs_json(liste) -> list[dict]:
    ids = [u.pk for u in liste]
    nb_reservations = reservations.nb_par_voyageur(ids)
    nb_annonces = hebergements.nb_annonces_par_hote(ids)
    return [_utilisateur(u, nb_reservations.get(u.pk, 0), nb_annonces.get(u.pk, 0)) for u in liste]


def _utilisateur(u, nb_reservations: int, nb_annonces: int) -> dict:
    return {
        'id': str(u.id), 'email': u.email, 'first_name': u.first_name, 'last_name': u.last_name,
        'role': u.role, 'phone': u.phone, 'avatar_url': u.avatar.url if u.avatar else None,
        'is_verified': u.is_verified, 'is_active': u.is_active,
        'date_joined': u.date_joined, 'last_login': u.last_login,
        'nb_reservations': nb_reservations, 'nb_annonces': nb_annonces,
        'conditions': _conditions(u),
        'candidature_hote': u.candidature_hote, 'candidature_motif': u.candidature_motif,
        'est_super_admin': u.is_superuser, 'admin_sections': u.admin_sections, 'admin_expire_le': u.admin_expire_le,
        'admin_permissions': u.admin_permissions or [],
    }


def _utilisateurs():
    return UserModel.objects.order_by('-date_joined')


def _lire_droits_admin(donnees) -> tuple[dict, dict]:
    """Admin limits sent by a super admin: (fields to write, errors)."""
    champs, erreurs = {}, {}
    if 'admin_sections' in donnees:
        sections = donnees['admin_sections']
        if sections is not None and not (isinstance(sections, list) and sections and set(sections) <= set(SECTIONS_ADMIN)):
            erreurs['admin_sections'] = ['Choisissez au moins une section valide, ou null pour toutes.']
        else:
            champs['admin_sections'] = sections
    if 'admin_permissions' in donnees:
        permissions = donnees['admin_permissions']
        if not (isinstance(permissions, list) and set(permissions) <= set(SPECIAL_PERMISSIONS)):
            erreurs['admin_permissions'] = ['Permissions inconnues.']
        else:
            champs['admin_permissions'] = sorted(set(permissions))
    if 'admin_expire_le' in donnees:
        valeur = donnees['admin_expire_le']
        date = parse_datetime(valeur) if isinstance(valeur, str) else None
        if valeur is not None and (date is None or timezone.is_naive(date) or date <= timezone.now()):
            erreurs['admin_expire_le'] = ['Date et heure à venir attendues, avec le fuseau, ou null.']
        else:
            champs['admin_expire_le'] = date
    return champs, erreurs


class DroitsAdminView(VueAdmin):
    """What the signed-in admin can do: the back-office menu follows it, the API enforces it on its own."""

    def get(self, request):
        u = request.user
        return Response({
            'est_super_admin': u.is_superuser,
            'sections': list(SECTIONS_ADMIN) if u.is_superuser or u.admin_sections is None else u.admin_sections,
            'sections_disponibles': [{'code': code, 'libelle': libelle} for code, libelle in SECTIONS_ADMIN.items()],
            'permissions': list(SPECIAL_PERMISSIONS) if u.is_superuser else list(u.admin_permissions or []),
            'permissions_disponibles': [{'code': code, 'libelle': libelle}
                                        for code, libelle in SPECIAL_PERMISSIONS.items()],
        })


class UtilisateurListView(VueAdmin):
    def get(self, request):
        qs = _utilisateurs()
        params = request.query_params
        if q := params.get('q', '').strip():
            qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone__icontains=q))
        if (role := params.get('role')) in ROLES:
            qs = qs.filter(role=role)
        if (actif := _booleen(params.get('actif'))) is not None:
            qs = qs.filter(is_active=actif)
        if (candidature := params.get('candidature')) in ('ouverte', 'refusee'):
            qs = qs.filter(candidature_hote=candidature)
        return _paginer(request, qs, _utilisateurs_json, en_lot=True)


class UtilisateurDetailView(VueAdmin):
    def patch(self, request, pk):
        if str(pk) == str(request.user.pk):
            return Response({'detail': 'Vous ne pouvez pas modifier votre propre compte.'}, status=status.HTTP_403_FORBIDDEN)
        cible = UserModel.objects.filter(pk=pk).first()
        if not cible:
            return _introuvable('Utilisateur')

        donnees = request.data
        role = donnees.get('role')
        if cible.is_superuser:
            return Response({'detail': 'Les super administrateurs se gèrent uniquement sur le serveur.'},
                            status=status.HTTP_403_FORBIDDEN)
        droits_admin = (cible.role == 'admin' or role == 'admin' or 'admin_sections' in donnees
                        or 'admin_permissions' in donnees or 'admin_expire_le' in donnees)
        if droits_admin and not request.user.is_superuser:
            return Response({'detail': 'Seuls les super administrateurs gèrent les comptes administrateurs.'},
                            status=status.HTTP_403_FORBIDDEN)
        if 'role' in donnees and role not in ROLES:
            return Response({'role': [f"Rôle invalide : {', '.join(ROLES)}."]}, status=status.HTTP_400_BAD_REQUEST)
        actif = donnees.get('is_active')
        if 'is_active' in donnees and not isinstance(actif, bool):
            return Response({'is_active': ['Valeur booléenne attendue.']}, status=status.HTTP_400_BAD_REQUEST)

        limites, erreurs = _lire_droits_admin(donnees)
        if erreurs:
            return Response(erreurs, status=status.HTTP_400_BAD_REQUEST)
        if limites and (role if 'role' in donnees else cible.role) != 'admin':
            return Response({'detail': 'Ces droits ne concernent que les administrateurs.'}, status=status.HTTP_400_BAD_REQUEST)

        trace = {'cible_id': str(cible.pk), 'cible_email': cible.email}
        if 'candidature' in donnees:
            erreur = _modifier_candidature(request, cible, donnees.get('candidature'), donnees.get('motif'))
            if erreur:
                return Response({'candidature': [erreur]}, status=status.HTTP_400_BAD_REQUEST)
        if 'role' in donnees and role != cible.role:
            activity.record('role_modifie', request, actor=request.user, avant=cible.role, apres=role, **trace)
            if role == 'admin':
                cible.role_avant_admin = cible.role
            elif cible.role == 'admin':
                cible.admin_sections, cible.admin_expire_le, cible.role_avant_admin = None, None, ''
                cible.admin_permissions = []
            cible.role = role
            if role != 'voyageur':
                cible.candidature_hote, cible.candidature_motif = '', ''
        if limites:
            for champ, valeur in limites.items():
                setattr(cible, champ, valeur)
            activity.record('droits_admin_modifies', request, actor=request.user, sections=cible.admin_sections,
                            permissions=cible.admin_permissions,
                            expire_le=cible.admin_expire_le.isoformat() if cible.admin_expire_le else None, **trace)
        if 'is_active' in donnees and actif != cible.is_active:
            cible.is_active = actif
            activity.record('compte_desactive' if not actif else 'compte_reactive', request, actor=request.user,
                            **trace)
        if 'conditions' in donnees:
            erreur = paiements.modifier_conditions_hote(cible, donnees.get('conditions'), request.user)
            if erreur:
                return Response({'conditions': [erreur]}, status=status.HTTP_400_BAD_REQUEST)
            activity.record('backoffice_modification', request, actor=request.user, objet='conditions_hote',
                            id=str(cible.pk), champs=['categorie', 'fondateur_debut', 'fondateur_fin'])
        cible.save(update_fields=['role', 'is_active', 'candidature_hote', 'candidature_motif', 'admin_sections',
                                  'admin_permissions', 'admin_expire_le', 'role_avant_admin'])
        if not cible.is_active:
            # Closes their sessions: without a valid refresh token, they are signed out at the latest when the access token expires
            revoquer_jetons(cible.pk)
        return Response(_utilisateurs_json([cible])[0])
