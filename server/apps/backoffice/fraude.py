"""Anti-fraud: bypass attempts (contact details, off-site payment) in messages and listings."""
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.securite.audit import journaliser
from apps.securite.models import AlerteFraudeModel
from apps.securite.permissions import EstAdministrateur

from .views import _nom, _paginer

LIBELLES = {'telephone': 'Téléphone', 'email': 'Email', 'lien': 'Lien', 'reseau': 'Réseau social',
            'application': 'Application de messagerie', 'hors_site': 'Paiement hors site'}


def _alerte(a: AlerteFraudeModel) -> dict:
    u = a.utilisateur
    return {
        'id': a.pk, 'cree_le': a.cree_le, 'contexte': a.contexte, 'contexte_libelle': a.get_contexte_display(),
        'objet_id': a.objet_id, 'types': [LIBELLES.get(t, t) for t in a.types], 'extraits': a.extraits,
        'masquee': a.masquee, 'traitee': a.traitee, 'traitee_le': a.traitee_le, 'note': a.note,
        'utilisateur': {'id': str(u.pk), 'nom': _nom(u), 'email': u.email, 'role': u.get_role_display(),
                        'nb_alertes': getattr(a, 'nb_alertes', None)},
    }


class AlertesView(APIView):
    """GET: alerts (?statut=a_traiter|traitees|toutes, ?q= email or name)."""
    permission_classes = [EstAdministrateur]

    def get(self, request):
        qs = AlerteFraudeModel.objects.select_related('utilisateur').annotate(
            nb_alertes=Count('utilisateur__alertes_fraude'))
        statut = request.query_params.get('statut', 'a_traiter')
        if statut == 'a_traiter':
            qs = qs.filter(traitee=False)
        elif statut == 'traitees':
            qs = qs.filter(traitee=True)
        if q := request.query_params.get('q', '').strip():
            qs = qs.filter(Q(utilisateur__email__icontains=q) | Q(utilisateur__first_name__icontains=q)
                           | Q(utilisateur__last_name__icontains=q))
        return _paginer(request, qs.order_by('-cree_le'), _alerte)


class AlerteTraiteeView(APIView):
    """POST {note}: alert reviewed (warning sent, account suspended… noted by the administrator)."""
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        alerte = AlerteFraudeModel.objects.select_related('utilisateur').filter(pk=pk).first()
        if not alerte:
            return Response({'detail': 'Alerte introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        alerte.traitee, alerte.traitee_le, alerte.traitee_par = True, timezone.now(), request.user
        alerte.note = str(request.data.get('note', ''))[:1000]
        alerte.save(update_fields=['traitee', 'traitee_le', 'traitee_par', 'note'])
        journaliser('backoffice_modification', request, utilisateur=request.user, objet='alerte_fraude', id=str(alerte.pk),
                    champs=['traitee'])
        return Response(_alerte(alerte))
