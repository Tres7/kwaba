"""Back-office: reviews (list, deletion with a reason)."""
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response

from apps.hebergements import api as hebergements
from apps.securite.audit import journaliser
from apps.users import api as users
from apps.securite.backoffice import VueAdmin, entier as _entier, introuvable as _introuvable, motif as _motif, nom as _nom, paginer as _paginer

from .models import AvisModel


def _avis(liste) -> list[dict]:
    annonces = hebergements.resumes({a.hebergement_id for a in liste})
    auteurs = users.comptes(a.auteur_id for a in liste)
    return [{
        'id': str(a.id), 'note': a.note, 'commentaire': a.commentaire,
        'auteur': {'id': str(a.auteur_id), 'nom': _nom(auteurs[a.auteur_id]) if a.auteur_id in auteurs else '',
                   'email': auteurs[a.auteur_id].email if a.auteur_id in auteurs else ''},
        'hebergement': {'id': str(a.hebergement_id), 'name': annonces[a.hebergement_id]['name'] if a.hebergement_id in annonces else ''},
        'reponse_hote': a.reponse_hote, 'created_at': a.created_at,
    } for a in liste]


class AvisListView(VueAdmin):
    def get(self, request):
        qs = AvisModel.objects.order_by('-created_at')
        params = request.query_params
        if q := params.get('q', '').strip():
            qs = qs.filter(Q(commentaire__icontains=q) | Q(hebergement_id__in=hebergements.ids_par_nom(q))
                           | Q(auteur_id__in=users.ids_par_recherche(q)))
        if (note := _entier(params.get('note'), 0, minimum=0)) in range(1, 6):
            qs = qs.filter(note=note)
        return _paginer(request, qs, _avis, en_lot=True)


class AvisDetailView(VueAdmin):
    def delete(self, request, pk):
        motif, erreur = _motif(request.query_params.get('motif'))
        if erreur:
            return erreur
        avis = AvisModel.objects.filter(pk=pk).first()
        if not avis:
            return _introuvable('Avis')
        annonce = hebergements.resumes([avis.hebergement_id]).get(avis.hebergement_id)
        trace = {'avis_id': str(avis.pk), 'annonce': annonce['name'] if annonce else '', 'auteur': getattr(users.compte(avis.auteur_id), 'email', ''),
                 'note': avis.note, 'motif': motif}
        avis.delete()  # the post_delete signal of the avis app computes the listing's rating again
        journaliser('avis_supprime', request, utilisateur=request.user, **trace)
        return Response(status=status.HTTP_204_NO_CONTENT)
