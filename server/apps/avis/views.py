import uuid

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.hebergements.models import HebergementModel
from apps.hebergements.serializers import HebergementSerializer
from .models import AvisModel, CRITERES
from .serializers import AvisCreateSerializer, AvisSerializer, ReponseHoteSerializer
from .services import motif_refus, recalculer_note, sejours_a_evaluer

PAGE_DEFAUT = 6
PAGE_MAX = 50


def _uuid(valeur):
    try:
        return uuid.UUID(str(valeur))
    except (ValueError, TypeError):
        return None


def _entier(valeur, defaut, minimum, maximum=None):
    try:
        nombre = int(valeur)
    except (ValueError, TypeError):
        return defaut
    if nombre < minimum:
        return defaut
    return min(nombre, maximum) if maximum is not None else nombre


class AvisListCreateView(APIView):
    """GET ?hebergement=<id>: public reviews + summary.  POST: leave a review on a finished stay."""

    def get_permissions(self):
        return [AllowAny()] if self.request.method == 'GET' else [IsAuthenticated()]

    def get(self, request):
        # Missing or malformed id: same response as an unknown listing (and not a 500 error)
        hebergement_id = _uuid(request.query_params.get('hebergement'))
        if hebergement_id is None:
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        hebergement = get_object_or_404(HebergementModel, pk=hebergement_id)
        qs = AvisModel.objects.filter(hebergement=hebergement).select_related('auteur', 'reservation')

        agregats = qs.aggregate(
            moyenne=Avg('note'), total=Count('id'),
            **{f'm_{c}': Avg(c) for c in CRITERES},
        )
        repartition = {n: 0 for n in range(5, 0, -1)}
        for ligne in qs.values('note').annotate(n=Count('id')):
            repartition[ligne['note']] = ligne['n']

        # Non-numeric or out-of-range value: default value (a negative limit would make the slicing fail)
        limit = _entier(request.query_params.get('limit'), defaut=PAGE_DEFAUT, minimum=1, maximum=PAGE_MAX)
        offset = _entier(request.query_params.get('offset'), defaut=0, minimum=0)

        return Response({
            'resume': {
                'moyenne': round(agregats['moyenne'], 2) if agregats['moyenne'] else None,
                'total': agregats['total'],
                'criteres': {c: (round(agregats[f'm_{c}'], 1) if agregats[f'm_{c}'] else None) for c in CRITERES},
                'libelles': CRITERES,
                'repartition': repartition,
            },
            'results': AvisSerializer(qs[offset:offset + limit], many=True).data,
            'count': agregats['total'],
        })

    def post(self, request):
        serializer = AvisCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reservation = serializer.validated_data['reservation']
        refus = motif_refus(reservation, request.user)
        if refus:
            return Response({'detail': refus}, status=status.HTTP_403_FORBIDDEN)

        try:
            with transaction.atomic():
                avis = serializer.save(auteur=request.user, hebergement_id=reservation.hebergement_id)
                recalculer_note(reservation.hebergement_id)
        except IntegrityError:
            return Response({'detail': "Vous avez déjà laissé un avis pour ce séjour."}, status=status.HTTP_409_CONFLICT)

        return Response(AvisSerializer(avis).data, status=status.HTTP_201_CREATED)


class AvisALaisserView(APIView):
    """Finished stays the user can still review."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        resultats = [
            {
                'reservation_id': str(r.id),
                'check_in': r.check_in,
                'check_out': r.check_out,
                'hebergement': HebergementSerializer(r.hebergement, context={'request': request}).data,
            }
            for r in sejours_a_evaluer(request.user)
        ]
        return Response({'results': resultats, 'count': len(resultats)})


class ReponseHoteView(APIView):
    """The host replies only once, publicly, to a review of their listing."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        avis = get_object_or_404(AvisModel.objects.select_related('hebergement'), pk=pk)
        if avis.hebergement.host_id != request.user.id:
            return Response({'detail': "Seul l'hôte de ce logement peut répondre."}, status=status.HTTP_403_FORBIDDEN)
        if avis.reponse_hote:
            return Response({'detail': 'Vous avez déjà répondu à cet avis.'}, status=status.HTTP_409_CONFLICT)

        serializer = ReponseHoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        avis.reponse_hote = serializer.validated_data['reponse'].strip()
        avis.reponse_le = timezone.now()
        avis.save(update_fields=['reponse_hote', 'reponse_le'])
        return Response(AvisSerializer(avis).data)
