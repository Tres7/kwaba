from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle

from config.prelancement import verifier_ouverture
from apps.export import api as export
from apps.hebergements import api as hebergements
from apps.paiements import api as paiements
from apps.users import api as users

from . import calendrier, paiement
from .models import ReservationModel
from .serializers import ReservationSerializer, ReservationCreateSerializer


class ReservationListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'reservation_creation'

    def get_throttles(self):
        # Only the creation: each booking holds its dates while it waits for payment
        return [ScopedRateThrottle()] if self.request.method == 'POST' else []

    def get(self, request):
        # ?as=host: bookings received on my listings
        vue_hote = request.query_params.get('as') == 'host'
        if vue_hote:
            qs = ReservationModel.objects.filter(hebergement_id__in=hebergements.ids_annonces_de(request.user.id))
        else:
            qs = ReservationModel.objects.filter(guest_id=request.user.pk)
        serializer = ReservationSerializer(users.attacher(qs, 'guest'), many=True,
                                           context={'request': request, 'vue_hote': vue_hote})
        return Response({'results': serializer.data, 'count': len(serializer.data)})

    def post(self, request):
        verifier_ouverture()
        if not paiements.reservation_possible():
            return Response({'detail': paiements.INDISPONIBLE}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        serializer = ReservationCreateSerializer(data=request.data, context={'request': request})
        with transaction.atomic():
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            reservation = serializer.save(guest_id=request.user.pk)
        return Response(ReservationSerializer(reservation, context={'request': request}).data, status=status.HTTP_201_CREATED)


class ReservationCalendrierView(APIView):
    """GET → .ics file of a paid stay, for the traveller's phone calendar. Only once paid: it gives the address and
    the landmark. Opened by a plain link (the site's proxy adds the session), so the phone opens it in its calendar."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        reservation = ReservationModel.objects.filter(pk=pk, guest_id=request.user.pk, status='confirmed').first()
        annonce = hebergements.fiche(reservation.hebergement_id, archivees=True) if reservation else None
        if not annonce:
            return Response({'detail': 'Réservation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        langue = request.query_params.get('langue')
        content = calendrier.evenement(reservation, annonce, langue if langue in ('fr', 'en') else 'fr')
        return export.ics_response(content, calendrier.nom_fichier(reservation))


class ReservationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk, user):
        try:
            return ReservationModel.objects.get(pk=pk, guest_id=user.pk)
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
            rembourse = paiement.annuler(obj, par='voyageur')
        except paiements.PaiementErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        numero_requis = paiements.numero_remboursement_requis('reservation', obj.pk)
        return Response({'detail': 'Réservation annulée.', 'rembourse': rembourse, 'numero_requis': numero_requis})
