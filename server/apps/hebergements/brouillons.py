"""Drafts of new listings: the host saves the form at any time and resumes it later (host space)."""
import json

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.securite import fraude
from apps.users import api as users
from apps.verifications import api as verifications

from . import soumission
from .models import BrouillonAnnonceModel, HebergementPhotoModel
from .serializers import HebergementCreateSerializer, HebergementSerializer

# Only the fields of the listing form are kept, checked for real when the draft is submitted
CHAMPS = frozenset(HebergementCreateSerializer.Meta.fields)
MAX_BROUILLONS = 10
TAILLE_MAX = 50_000  # characters of JSON: a full form is far below


def erreurs(donnees: dict) -> dict:
    """What the API would refuse among the answers already given: shown early, never a reason not to save them."""
    remplis = {cle: valeur for cle, valeur in donnees.items() if valeur not in (None, '')}
    controle = HebergementCreateSerializer(data=remplis, partial=True)
    controle.is_valid()
    return controle.errors


class BrouillonSerializer(serializers.ModelSerializer):
    etape = serializers.RegexField(r'^[a-z0-9-]*$', max_length=30, required=False, allow_blank=True)

    class Meta:
        model = BrouillonAnnonceModel
        fields = ['id', 'donnees', 'etape', 'cree_le', 'modifie_le']
        read_only_fields = ['id', 'cree_le', 'modifie_le']

    def validate_donnees(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Objet attendu.")
        value = {cle: valeur for cle, valeur in value.items() if cle in CHAMPS}
        if len(json.dumps(value)) > TAILLE_MAX:
            raise serializers.ValidationError("Brouillon trop volumineux.")
        return value


class BrouillonsView(APIView):
    """GET: the host's drafts, the most recent first. POST {donnees}: a new draft."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        brouillons = BrouillonAnnonceModel.objects.filter(host_id=request.user.pk)
        return Response({'results': BrouillonSerializer(brouillons, many=True).data})

    def post(self, request):
        if not users.peut_gerer_annonces(request.user):
            return Response({'detail': 'Seuls les hôtes peuvent créer une annonce.'}, status=status.HTTP_403_FORBIDDEN)
        if BrouillonAnnonceModel.objects.filter(host_id=request.user.pk).count() >= MAX_BROUILLONS:
            return Response({'detail': f"{MAX_BROUILLONS} brouillons au plus : terminez ou supprimez-en un."},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = BrouillonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(host_id=request.user.pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BrouillonDetailView(APIView):
    """GET, PUT {donnees} (replaces the saved fields), PATCH {donnees?, etape?} (wizard: merges the answers of a
    screen and returns `erreurs`), DELETE. Only the draft's host."""
    permission_classes = [IsAuthenticated]

    def _brouillon(self, request, pk):
        return BrouillonAnnonceModel.objects.filter(pk=pk, host_id=request.user.pk).first()

    def get(self, request, pk):
        brouillon = self._brouillon(request, pk)
        if not brouillon:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(BrouillonSerializer(brouillon).data)

    def put(self, request, pk):
        brouillon = self._brouillon(request, pk)
        if not brouillon:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = BrouillonSerializer(brouillon, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, pk):
        brouillon = self._brouillon(request, pk)
        if not brouillon:
            return Response(status=status.HTTP_404_NOT_FOUND)
        reponses = request.data.get('donnees', {})
        if not isinstance(reponses, dict):
            return Response({'donnees': ["Objet attendu."]}, status=status.HTTP_400_BAD_REQUEST)
        modifications = {'donnees': {**brouillon.donnees, **reponses}}
        if 'etape' in request.data:
            modifications['etape'] = request.data['etape']
        serializer = BrouillonSerializer(brouillon, data=modifications, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({**serializer.data, 'erreurs': erreurs(serializer.instance.donnees)})

    def delete(self, request, pk):
        brouillon = self._brouillon(request, pk)
        if not brouillon:
            return Response(status=status.HTTP_404_NOT_FOUND)
        brouillon.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BrouillonConditionsView(APIView):
    """GET: what the host has done and what is left before sending this draft (see soumission.conditions)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        brouillon = BrouillonAnnonceModel.objects.filter(pk=pk, host_id=request.user.pk).first()
        if not brouillon:
            return Response(status=status.HTTP_404_NOT_FOUND)
        etat = soumission.conditions(request.user, brouillon.donnees)
        return Response({**etat, 'bloquants': soumission.bloquants(etat)})


class BrouillonSoumissionView(APIView):
    """POST: sends the draft for verification. Everything is checked again here, in one transaction: the listing is
    created, its photos attached to it and the draft deleted, or nothing happens."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        if not users.peut_gerer_annonces(request.user):
            return Response({'detail': 'Seuls les hôtes peuvent créer une annonce.'}, status=status.HTTP_403_FORBIDDEN)
        # Locked: a double click cannot create the listing twice
        brouillon = BrouillonAnnonceModel.objects.select_for_update().filter(pk=pk, host_id=request.user.pk).first()
        if not brouillon:
            return Response(status=status.HTTP_404_NOT_FOUND)

        bloquants = soumission.bloquants(soumission.conditions(request.user, brouillon.donnees))
        if bloquants:
            return Response({'detail': "Il reste des étapes à terminer.", 'code': 'conditions', 'bloquants': bloquants},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            verifications.verifier_limite_annonces(request.user)
        except verifications.VerificationErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = HebergementCreateSerializer(data=brouillon.donnees)
        if not serializer.is_valid():
            trouvailles = getattr(serializer, 'trouvailles', None)
            if trouvailles:
                fraude.signaler(request.user.id, 'annonce', 'nouvelle', trouvailles)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        hebergement = serializer.save(host_id=request.user.pk, attestation_le=timezone.now())
        HebergementPhotoModel.objects.filter(
            owner_id=request.user.pk, pk__in=soumission.ids_photos(brouillon.donnees['images']),
        ).update(hebergement_id=hebergement.pk)
        brouillon.delete()
        verifications.visite_a_planifier(hebergement.id)
        return Response(HebergementSerializer(hebergement, context={'request': request, 'proprietaire': True}).data,
                        status=status.HTTP_201_CREATED)
