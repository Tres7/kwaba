"""Drafts of new listings: the host saves the form at any time and resumes it later (host space)."""
import json

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BrouillonAnnonceModel
from .serializers import HebergementCreateSerializer
from .views import HOST_ROLES

# Only the fields of the listing form are kept, checked for real when the draft is submitted
CHAMPS = frozenset(HebergementCreateSerializer.Meta.fields)
MAX_BROUILLONS = 10
TAILLE_MAX = 50_000  # characters of JSON: a full form is far below


class BrouillonSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrouillonAnnonceModel
        fields = ['id', 'donnees', 'cree_le', 'modifie_le']
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
        if request.user.role not in HOST_ROLES:
            return Response({'detail': 'Seuls les hôtes peuvent créer une annonce.'}, status=status.HTTP_403_FORBIDDEN)
        if BrouillonAnnonceModel.objects.filter(host_id=request.user.pk).count() >= MAX_BROUILLONS:
            return Response({'detail': f"{MAX_BROUILLONS} brouillons au plus : terminez ou supprimez-en un."},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = BrouillonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(host_id=request.user.pk)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BrouillonDetailView(APIView):
    """GET, PUT {donnees} (replaces the saved fields), DELETE. Only the draft's host."""
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

    def delete(self, request, pk):
        brouillon = self._brouillon(request, pk)
        if not brouillon:
            return Response(status=status.HTTP_404_NOT_FOUND)
        brouillon.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

