"""Back-office: listings (list, publication, archiving and restoring)."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.reservations import api as reservations_api
from apps.activity import api as activity
from apps.securite.backoffice import (
    VueAdmin, booleen as _booleen, introuvable as _introuvable, motif as _motif, nom as _nom, paginer as _paginer,
)
from apps.securite.permissions import has_special_permission
from apps.users import api as users
from apps.verifications import api as verifications

from . import api as hebergements_api
from .archivage import ArchivageImpossible, archiver, restaurer
from .models import HebergementModel


def _hebergements_json(liste) -> list[dict]:
    liste = users.attacher(liste, 'host')
    nb_reservations = reservations_api.nb_par_annonce(h.id for h in liste)
    return [{
        'id': str(h.id), 'name': h.name, 'type': h.type, 'city': h.city, 'location': h.location,
        'price_per_night': h.price_per_night, 'image_url': h.image_url, 'is_available': h.is_available,
        'est_verifie': h.statut_verification == 'verifiee', 'statut_verification': h.statut_verification,
        'rating': h.rating, 'review_count': h.review_count, 'nb_reservations': nb_reservations.get(h.id, 0),
        'host': {'id': str(h.host_id), 'nom': _nom(h.host) if h.host else '', 'email': h.host.email if h.host else ''},
        'created_at': h.created_at, 'archivee_le': h.archivee_le,
        'validated_without_visit_at': h.validated_without_visit_at,
        'validated_without_visit_reason': h.validated_without_visit_reason,
    } for h in liste]


def _hebergement(h) -> dict:
    return _hebergements_json([h])[0]


def _hebergements(archivees=False):
    qs = HebergementModel.tous.filter(archivee_le__isnull=False) if archivees else HebergementModel.objects.all()
    return qs.order_by('-created_at')


class HebergementListView(VueAdmin):
    def get(self, request):
        params = request.query_params
        qs = _hebergements(archivees=_booleen(params.get('archivees')) is True)
        if q := params.get('q', '').strip():
            qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q) | Q(location__icontains=q) | Q(host_id__in=users.ids_par_recherche(q)))
        if ville := params.get('ville', '').strip():
            qs = qs.filter(city__iexact=ville)
        if (visible := _booleen(params.get('visible'))) is not None:
            qs = qs.filter(is_available=visible)
        if (verifie := _booleen(params.get('verifie'))) is not None:
            qs = qs.filter(statut_verification='verifiee') if verifie else qs.exclude(statut_verification='verifiee')
        if (statut := params.get('statut', '')) in dict(HebergementModel.STATUTS_VERIFICATION):
            qs = qs.filter(statut_verification=statut)
        return _paginer(request, qs, _hebergements_json, en_lot=True)


class HebergementDetailView(VueAdmin):
    def patch(self, request, pk):
        annonce = HebergementModel.objects.filter(pk=pk).first()
        if not annonce:
            return _introuvable('Annonce')

        donnees = request.data
        for champ in ('is_available', 'est_verifie'):
            if champ in donnees and not isinstance(donnees[champ], bool):
                return Response({champ: ['Valeur booléenne attendue.']}, status=status.HTTP_400_BAD_REQUEST)

        validate_without_visit = (donnees.get('est_verifie') is True and annonce.statut_verification != 'verifiee')
        if validate_without_visit:
            if not has_special_permission(request.user, 'validate_without_visit'):
                return Response({'detail': "La validation sans visite ne vous est pas ouverte."},
                                status=status.HTTP_403_FORBIDDEN)
            reason, erreur = _motif(donnees.get('motif'))
            if erreur:
                return erreur
            keep_visit = donnees.get('keep_visit', False)
            if not isinstance(keep_visit, bool):
                return Response({'keep_visit': ['Valeur booléenne attendue.']}, status=status.HTTP_400_BAD_REQUEST)

        changements = {}
        if 'is_available' in donnees and donnees['is_available'] != annonce.is_available:
            changements['is_available'] = annonce.is_available = donnees['is_available']
        a_verifier = False
        if 'est_verifie' in donnees and donnees['est_verifie'] != (annonce.statut_verification == 'verifiee'):
            # Validating here publishes the listing without an agent visit; removing the validation takes it off the site
            # and tells the agents that a visit is needed
            annonce.statut_verification = 'verifiee' if donnees['est_verifie'] else 'en_attente'
            if donnees['est_verifie']:
                annonce.motif_refus = ''
                annonce.validated_without_visit_at = timezone.now()
                annonce.validated_without_visit_by_id = request.user.pk
                annonce.validated_without_visit_reason = reason
            else:
                annonce.validated_without_visit_at = annonce.validated_without_visit_by_id = None
                annonce.validated_without_visit_reason = ''
            changements['statut_verification'] = annonce.statut_verification
            a_verifier = not donnees['est_verifie']

        if changements:
            with transaction.atomic():
                annonce.save()
                activity.record('annonce_modifiee', request, actor=request.user,
                                annonce_id=str(annonce.pk), annonce=annonce.name, **changements)
                if validate_without_visit:
                    activity.record('validated_without_visit', request, actor=request.user,
                                    annonce_id=str(annonce.pk), motif=reason, keep_visit=keep_visit)
                    verifications.validated_without_visit(hebergements_api.fiche(annonce.pk), request.user, reason,
                                                          keep_visit)
            if a_verifier:
                verifications.visite_a_planifier(annonce.id)
        return Response(_hebergement(_hebergements().get(pk=annonce.pk)))

    def delete(self, request, pk):
        motif, erreur = _motif(request.query_params.get('motif'))
        if erreur:
            return erreur
        annonce = HebergementModel.objects.filter(pk=pk).first()
        if not annonce:
            return _introuvable('Annonce')
        trace = {'annonce_id': str(annonce.pk), 'annonce': annonce.name, 'hote': annonce.host.email, 'motif': motif}
        try:
            archiver(annonce)
        except ArchivageImpossible as e:
            return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        activity.record('annonce_supprimee', request, actor=request.user, **trace)
        return Response(status=status.HTTP_204_NO_CONTENT)


class HebergementRestaurerView(VueAdmin):
    def post(self, request, pk):
        annonce = HebergementModel.tous.filter(pk=pk, archivee_le__isnull=False).first()
        if not annonce:
            return _introuvable('Annonce archivée')
        restaurer(annonce)
        activity.record('annonce_restauree', request, actor=request.user, annonce_id=str(annonce.pk),
                        annonce=annonce.name, hote=annonce.host.email)
        return Response(_hebergement(_hebergements().get(pk=annonce.pk)))


