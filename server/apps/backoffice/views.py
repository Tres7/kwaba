"""Back-office API. Contract: documentation/modules/backoffice-api.md.

Every view requires the admin role, read from the database at every request (EstAdministrateur). Every write is
recorded in the audit log (apps.securite) with the administrator, the target and the reason.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.avis import api as avis_api
from apps.hebergements import api as hebergements
from apps.paiements import api as paiements
from apps.reservations import api as reservations_api
from apps.securite.audit import journaliser
from apps.securite.backoffice import (
    VueAdmin, booleen as _booleen, introuvable as _introuvable, paginer as _paginer,
)
from apps.users.infrastructure.http.controllers.AuthController import revoquer_jetons

User = get_user_model()

ROLES = [code for code, _ in User.ROLE_CHOICES]


# --- 1. Tableau de bord -----------------------------------------------------------------------------

class StatsView(VueAdmin):
    def get(self, request):
        maintenant = timezone.now()
        aujourd_hui = timezone.localdate()
        premier_jour = aujourd_hui - timedelta(days=29)
        il_y_a_30j = maintenant - timedelta(days=30)

        utilisateurs = User.objects.aggregate(
            total=Count('id'),
            nouveaux_30j=Count('id', filter=Q(date_joined__gte=il_y_a_30j)),
            hotes=Count('id', filter=Q(role='hote')),
            desactives=Count('id', filter=Q(is_active=False)),
        )
        annonces = hebergements.statistiques()
        reservations = reservations_api.statistiques(il_y_a_30j)
        avis = avis_api.statistiques()

        # One entry per day over 30 days (today included), 0 on days without a confirmed booking
        par_jour = reservations_api.confirmees_par_jour(premier_jour)
        serie = []
        for decalage in range(30):
            jour = premier_jour + timedelta(days=decalage)
            ligne = par_jour.get(jour, {})
            serie.append({'date': jour.isoformat(), 'nombre': ligne.get('nombre', 0), 'volume': int(ligne.get('volume') or 0)})

        return Response({
            'utilisateurs': utilisateurs,
            'annonces': annonces,
            'reservations': reservations,
            'avis': avis,
            'reservations_par_jour': serie,
        })


# --- 2. Utilisateurs --------------------------------------------------------------------------------

def _conditions(u) -> dict | None:
    """Host's commission: category, Founders Programme and rate applied today."""
    return paiements.conditions_commission(u) if u.role == 'hote' else None


def _utilisateur(u) -> dict:
    return {
        'id': str(u.id), 'email': u.email, 'first_name': u.first_name, 'last_name': u.last_name,
        'role': u.role, 'phone': u.phone, 'avatar_url': u.avatar.url if u.avatar else None,
        'is_verified': u.is_verified, 'is_active': u.is_active,
        'date_joined': u.date_joined, 'last_login': u.last_login,
        'nb_reservations': u.nb_reservations, 'nb_annonces': u.nb_annonces,
        'conditions': _conditions(u),
    }


def _utilisateurs():
    return User.objects.annotate(
        nb_reservations=Count('reservations', distinct=True),
        nb_annonces=Count('hebergements', distinct=True),
    ).order_by('-date_joined')


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
        return _paginer(request, qs, _utilisateur)


class UtilisateurDetailView(VueAdmin):
    def patch(self, request, pk):
        if str(pk) == str(request.user.pk):
            return Response({'detail': 'Vous ne pouvez pas modifier votre propre compte.'}, status=status.HTTP_403_FORBIDDEN)
        cible = User.objects.filter(pk=pk).first()
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
        if 'role' in donnees and role != cible.role:
            journaliser('role_modifie', request, utilisateur=request.user, avant=cible.role, apres=role, **trace)
            cible.role = role
        if 'is_active' in donnees and actif != cible.is_active:
            cible.is_active = actif
            journaliser('compte_desactive' if not actif else 'compte_reactive', request, utilisateur=request.user, **trace)
        if 'conditions' in donnees:
            erreur = paiements.modifier_conditions_hote(cible, donnees.get('conditions'), request.user)
            if erreur:
                return Response({'conditions': [erreur]}, status=status.HTTP_400_BAD_REQUEST)
            journaliser('backoffice_modification', request, utilisateur=request.user, objet='conditions_hote',
                        id=str(cible.pk), champs=['categorie', 'fondateur_debut', 'fondateur_fin'])
        cible.save(update_fields=['role', 'is_active'])
        if not cible.is_active:
            # Closes their sessions: without a valid refresh token, they are signed out at the latest when the access token expires
            revoquer_jetons(cible.pk)
        return Response(_utilisateur(_utilisateurs().get(pk=cible.pk)))
