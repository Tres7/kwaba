"""Back-office API. Contract: documentation/modules/backoffice-api.md.

Every view requires the admin role, read from the database at every request (EstAdministrateur). Every write is
recorded in the audit log (apps.securite) with the administrator, the target and the reason.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework.response import Response

from apps.avis import api as avis_api
from apps.hebergements import api as hebergements
from apps.reservations import api as reservations_api
from apps.securite.backoffice import VueAdmin
from apps.users import api as users


# --- 1. Tableau de bord -----------------------------------------------------------------------------

class StatsView(VueAdmin):
    def get(self, request):
        maintenant = timezone.now()
        aujourd_hui = timezone.localdate()
        premier_jour = aujourd_hui - timedelta(days=29)
        il_y_a_30j = maintenant - timedelta(days=30)

        utilisateurs = users.statistiques(il_y_a_30j)
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
