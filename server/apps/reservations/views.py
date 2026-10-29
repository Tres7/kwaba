from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from config.prelancement import verifier_ouverture
from apps.paiements import services as paiements

from .models import ReservationModel
from .serializers import ReservationSerializer, ReservationCreateSerializer


class ReservationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ?as=host: bookings received on my listings
        if request.query_params.get('as') == 'host':
            qs = ReservationModel.objects.filter(hebergement__host=request.user)
        else:
            qs = ReservationModel.objects.filter(guest=request.user)
        # hebergement__host__piece_identite: "verified host" badge of the nested listing (one query per booking otherwise)
        qs = (qs.select_related('hebergement', 'hebergement__host', 'hebergement__host__piece_identite', 'guest')
              .prefetch_related('paiements', 'remboursements'))
        serializer = ReservationSerializer(qs, many=True, context={'request': request})
        return Response({'results': serializer.data, 'count': len(serializer.data)})

    def post(self, request):
        verifier_ouverture()
        if not paiements.reservation_possible():
            return Response({'detail': paiements.INDISPONIBLE}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        serializer = ReservationCreateSerializer(data=request.data, context={'request': request})
        with transaction.atomic():
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            reservation = serializer.save(guest=request.user)
        return Response(ReservationSerializer(reservation, context={'request': request}).data, status=status.HTTP_201_CREATED)


class ReservationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk, user):
        try:
            return ReservationModel.objects.select_related('hebergement', 'guest').get(pk=pk, guest=user)
        except ReservationModel.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get_object(pk, request.user)
        if not obj:
            return Response({'detail': 'Réservation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ReservationSerializer(obj, context={'request': request}).data)

    def delete(self, request, pk):
        obj = self._get_object(pk, request.user)
        if not obj:
            return Response({'detail': 'Réservation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if obj.check_in <= timezone.localdate():
            return Response(
                {'detail': 'Un séjour déjà commencé ou passé ne peut plus être annulé.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if obj.status not in ('confirmed', 'pending'):
            return Response({'detail': 'Cette réservation ne peut pas être annulée.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rembourse = paiements.annuler(obj, par='voyageur')
        except paiements.PaiementErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        numero_requis = obj.remboursements.filter(statut='attente_numero').exists()
        return Response({'detail': 'Réservation annulée.', 'rembourse': rembourse, 'numero_requis': numero_requis})
