"""Payment of a stay by the traveller: payment page, return page, Mobile Money account for a refund.

Served under /api/v1/paiements/reservations/ (config/urls.py), as before the stays had their own module."""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.prelancement import verifier_ouverture
from apps.paiements import api as paiements

from . import paiement
from .models import ReservationModel


def _reservation_du_voyageur(pk, user):
    return ReservationModel.objects.select_related('guest').filter(pk=pk, guest=user).first()


class PayerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        verifier_ouverture()
        reservation = _reservation_du_voyageur(pk, request.user)
        if not reservation:
            return Response({'detail': 'Réservation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        moyen = request.data.get('moyen') or reservation.payment_method
        try:
            url = paiement.demarrer_paiement(reservation, moyen)
        except paiements.PaiementErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'url': url})


class StatutView(APIView):
    """Polled by the return page after payment: reads the transaction again from FedaPay if needed."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        reservation = _reservation_du_voyageur(pk, request.user)
        if not reservation:
            return Response({'detail': 'Réservation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if paiements.synchroniser_dernier_paiement('reservation', reservation.pk):
            reservation.refresh_from_db()
        return Response({
            'reservation': reservation.status,
            'paiement': paiements.etats_paiement('reservation', [reservation.pk])[reservation.pk]['paiement'],
            'expire_le': reservation.expire_le,
            'annule_par': reservation.annule_par,
        })


class CompteRemboursementView(APIView):
    """The traveller gives the Mobile Money account to be refunded on."""
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        reservation = _reservation_du_voyageur(pk, request.user)
        if not reservation:
            return Response({'detail': 'Réservation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = paiements.CompteRemboursementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not paiements.indiquer_numero_remboursement('reservation', reservation.pk, **serializer.validated_data):
            return Response({'detail': "Aucun remboursement n'attend de numéro pour cette réservation."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Numéro enregistré : le remboursement va être envoyé.'})
