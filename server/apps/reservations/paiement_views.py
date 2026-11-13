"""Payment of a stay: by the traveller (payment page, return page, Mobile Money account for a refund), or by a third
party the traveller asks (secret link, payer's page and return page: see tiers.py).

Served under /api/v1/paiements/ (config/urls.py), as before the stays had their own module."""
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.prelancement import verifier_ouverture
from apps.paiements import api as paiements
from apps.activity import api as activity

from . import paiement, tiers
from .models import DemandePaiementModel, ReservationModel


class _LimiteEcritures:
    """Writes limited per user (scope paiement_tiers): links created, payments started."""
    throttle_scope = 'paiement_tiers'

    def get_throttles(self):
        return [ScopedRateThrottle()] if self.request.method in ('POST', 'PUT', 'DELETE') else []


def _reservation_du_voyageur(pk, user):
    return ReservationModel.objects.filter(pk=pk, guest_id=user.pk).first()


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


# --- Payment by a third party -----------------------------------------------------------------------------------------

def _etat_demande(demande) -> dict:
    return {'active': bool(demande), 'expire_le': demande.expire_le if demande else None,
            'groupe': bool(demande and demande.voyage_id)}


class DemandeTiersView(_LimiteEcritures, APIView):
    """The traveller asks someone else to pay the booking: state of the request, new secret link, link disabled."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        reservation = _reservation_du_voyageur(pk, request.user)
        if not reservation:
            return Response({'detail': 'Réservation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_etat_demande(tiers.demande_active(reservation)))

    def post(self, request, pk):
        verifier_ouverture()
        reservation = _reservation_du_voyageur(pk, request.user)
        if not reservation:
            return Response({'detail': 'Réservation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            demande, jeton = tiers.creer_lien(reservation)
        except paiements.PaiementErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        activity.record('paiement_tiers_lien', request, actor=request.user, reservation=str(reservation.pk))
        # The only time the link is given: only its fingerprint is kept
        return Response({**_etat_demande(demande), 'lien': f"{settings.FRONTEND_URL}/payer/{jeton}"},
                        status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        reservation = _reservation_du_voyageur(pk, request.user)
        if not reservation:
            return Response({'detail': 'Réservation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        tiers.revoquer(reservation)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PaiementTiersView(_LimiteEcritures, APIView):
    """Page of the payer, reached by the secret link: what they pay (GET), starting the payment (POST {moyen})."""
    permission_classes = [IsAuthenticated]

    def _demande(self, jeton):
        return tiers.demande_par_jeton(jeton)

    def get(self, request, jeton):
        demande = self._demande(jeton)
        if not demande:
            return Response({'detail': 'Lien de paiement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(tiers.apercu(demande, request.user))

    def post(self, request, jeton):
        verifier_ouverture()
        demande = self._demande(jeton)
        if not demande:
            return Response({'detail': 'Lien de paiement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            url = tiers.payer(demande, request.user, request.data.get('moyen') or 'mobile_money')
        except paiements.PaiementErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        activity.record('paiement_tiers_demarre', request, actor=request.user, reservation=str(demande.reservation_id))
        return Response({'url': url})


class StatutTiersView(APIView):
    """Return page of the payer after the provider's page: status of the payment they started."""
    permission_classes = [IsAuthenticated]

    def get(self, request, demande_id):
        demande = DemandePaiementModel.objects.select_related('reservation').filter(pk=demande_id).first()
        statut = tiers.statut_pour_payeur(demande, request.user) if demande else None
        if statut is None:
            return Response({'detail': 'Paiement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(statut)
