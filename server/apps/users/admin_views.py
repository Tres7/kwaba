"""Back-office: user accounts (list, role, deactivation, host commission). Contract: documentation/modules/backoffice-api.md."""
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from apps.hebergements import api as hebergements
from apps.paiements import api as paiements
from apps.reservations import api as reservations
from apps.securite.audit import journaliser
from apps.securite.backoffice import VueAdmin, booleen as _booleen, introuvable as _introuvable, paginer as _paginer

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
        journaliser('candidature_refusee', request, utilisateur=request.user, cible_id=str(cible.pk), motif=motif)
    elif valeur == 'ouverte' and cible.candidature_hote == 'refusee':
        cible.candidature_hote, cible.candidature_motif = 'ouverte', ''
        journaliser('candidature_ouverte', request, utilisateur=request.user, cible_id=str(cible.pk))
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
    }


def _utilisateurs():
    return UserModel.objects.order_by('-date_joined')


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
        if 'role' in donnees and role not in ROLES:
            return Response({'role': [f"Rôle invalide : {', '.join(ROLES)}."]}, status=status.HTTP_400_BAD_REQUEST)
        actif = donnees.get('is_active')
        if 'is_active' in donnees and not isinstance(actif, bool):
            return Response({'is_active': ['Valeur booléenne attendue.']}, status=status.HTTP_400_BAD_REQUEST)

        trace = {'cible_id': str(cible.pk), 'cible_email': cible.email}
        if 'candidature' in donnees:
            erreur = _modifier_candidature(request, cible, donnees.get('candidature'), donnees.get('motif'))
            if erreur:
                return Response({'candidature': [erreur]}, status=status.HTTP_400_BAD_REQUEST)
        if 'role' in donnees and role != cible.role:
            journaliser('role_modifie', request, utilisateur=request.user, avant=cible.role, apres=role, **trace)
            cible.role = role
            if role != 'voyageur':
                cible.candidature_hote, cible.candidature_motif = '', ''
        if 'is_active' in donnees and actif != cible.is_active:
            cible.is_active = actif
            journaliser('compte_desactive' if not actif else 'compte_reactive', request, utilisateur=request.user, **trace)
        if 'conditions' in donnees:
            erreur = paiements.modifier_conditions_hote(cible, donnees.get('conditions'), request.user)
            if erreur:
                return Response({'conditions': [erreur]}, status=status.HTTP_400_BAD_REQUEST)
            journaliser('backoffice_modification', request, utilisateur=request.user, objet='conditions_hote',
                        id=str(cible.pk), champs=['categorie', 'fondateur_debut', 'fondateur_fin'])
        cible.save(update_fields=['role', 'is_active', 'candidature_hote', 'candidature_motif'])
        if not cible.is_active:
            # Closes their sessions: without a valid refresh token, they are signed out at the latest when the access token expires
            revoquer_jetons(cible.pk)
        return Response(_utilisateurs_json([cible])[0])
