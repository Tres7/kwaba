"""Anti-fraud: bypass attempts (contact details, off-site payment) in messages and listings."""
from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.securite.audit import journaliser
from apps.securite.models import AlerteFraudeModel
from apps.securite.permissions import EstAdministrateur
from apps.users import api as users

from apps.securite.backoffice import nom as _nom, paginer as _paginer

LIBELLES = {'telephone': 'Téléphone', 'email': 'Email', 'lien': 'Lien', 'reseau': 'Réseau social',
            'application': 'Application de messagerie', 'hors_site': 'Paiement hors site'}


def _alertes(alertes: list[AlerteFraudeModel]) -> list[dict]:
    comptes = users.comptes(a.utilisateur_id for a in alertes)
    nb = dict(AlerteFraudeModel.objects.filter(utilisateur_id__in=comptes).values('utilisateur_id')
              .annotate(n=Count('id')).values_list('utilisateur_id', 'n'))
    return [_alerte(a, comptes.get(a.utilisateur_id), nb.get(a.utilisateur_id, 0)) for a in alertes]


def _alerte(a: AlerteFraudeModel, u, nb_alertes: int | None = None) -> dict:
    return {
        'id': a.pk, 'cree_le': a.cree_le, 'contexte': a.contexte, 'contexte_libelle': a.get_contexte_display(),
        'objet_id': a.objet_id, 'types': [LIBELLES.get(t, t) for t in a.types], 'extraits': a.extraits,
        'masquee': a.masquee, 'traitee': a.traitee, 'traitee_le': a.traitee_le, 'note': a.note,
        'utilisateur': {'id': str(a.utilisateur_id), 'nom': _nom(u) if u else '', 'email': u.email if u else '',
                        'role': u.get_role_display() if u else '', 'nb_alertes': nb_alertes},
    }


class AlertesView(APIView):
    """GET: alerts (?statut=a_traiter|traitees|toutes, ?q= email or name)."""
    permission_classes = [EstAdministrateur]

    def get(self, request):
        qs = AlerteFraudeModel.objects.all()
        statut = request.query_params.get('statut', 'a_traiter')
        if statut == 'a_traiter':
            qs = qs.filter(traitee=False)
        elif statut == 'traitees':
            qs = qs.filter(traitee=True)
        if q := request.query_params.get('q', '').strip():
            qs = qs.filter(utilisateur_id__in=users.ids_par_recherche(q))
        return _paginer(request, qs.order_by('-cree_le'), _alertes, en_lot=True)


class AlerteTraiteeView(APIView):
    """POST {note}: alert reviewed (warning sent, account suspended… noted by the administrator)."""
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        alerte = AlerteFraudeModel.objects.filter(pk=pk).first()
        if not alerte:
            return Response({'detail': 'Alerte introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        alerte.traitee, alerte.traitee_le, alerte.traitee_par_id = True, timezone.now(), request.user.pk
        alerte.note = str(request.data.get('note', ''))[:1000]
        alerte.save(update_fields=['traitee', 'traitee_le', 'traitee_par_id', 'note'])
        journaliser('backoffice_modification', request, utilisateur=request.user, objet='alerte_fraude', id=str(alerte.pk),
                    champs=['traitee'])
        return Response(_alerte(alerte, users.compte(alerte.utilisateur_id)))
