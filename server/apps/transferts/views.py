import uuid
from datetime import datetime

from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.prelancement import verifier_ouverture
from apps.paiements import services as paiements
from apps.paiements.views import CompteRemboursementSerializer
from apps.reservations.models import ReservationModel

from . import services, tarifs
from .models import AeroportModel, TransfertModel


class AeroportSerializer(serializers.ModelSerializer):
    # Price of each vehicle from this airport (the same by day and by night): shown before any choice
    prix = serializers.SerializerMethodField()

    class Meta:
        model = AeroportModel
        fields = ['code', 'nom', 'ville', 'pays', 'fuseau', 'prix']

    def get_prix(self, obj):
        return {t.categorie: t.prix for t in obj.tarifs.all() if t.actif}


class TransfertSerializer(serializers.ModelSerializer):
    aeroport_detail = AeroportSerializer(source='aeroport', read_only=True)
    reference = serializers.CharField(read_only=True)
    vehicule = serializers.SerializerMethodField()
    arrivee_locale = serializers.SerializerMethodField()
    chauffeur = serializers.SerializerMethodField()
    paiement = serializers.SerializerMethodField()
    remboursement = serializers.SerializerMethodField()
    annulation_gratuite = serializers.SerializerMethodField()

    class Meta:
        model = TransfertModel
        fields = [
            'id', 'reference', 'aeroport', 'aeroport_detail', 'arrivee', 'arrivee_locale', 'numero_vol', 'passagers',
            'bagages', 'categorie', 'vehicule', 'destination', 'telephone', 'message', 'reservation', 'prix',
            'majoration_nuit', 'moyen', 'statut', 'expire_le', 'annule_par', 'chauffeur', 'paiement', 'remboursement',
            'annulation_gratuite', 'cree_le',
        ]

    def get_vehicule(self, obj):
        return tarifs.CATEGORIES[obj.categorie]

    def get_arrivee_locale(self, obj):
        """Arrival time in the airport's time zone, without offset: it is the one of the plane ticket."""
        return obj.arrivee.astimezone(services.ZoneInfo(obj.aeroport.fuseau)).strftime('%Y-%m-%dT%H:%M')

    def get_chauffeur(self, obj):
        # Contact details visible to the traveller once the driver is assigned
        c = obj.chauffeur
        if not c or obj.statut not in ('chauffeur_assigne', 'termine'):
            return None
        return {'nom': f"{c.prenom} {c.nom}", 'telephone': c.telephone, 'vehicule': c.vehicule,
                'immatriculation': c.immatriculation}

    def get_paiement(self, obj):
        dernier = max(obj.paiements.all(), key=lambda p: p.cree_le, default=None)
        return dernier.statut if dernier else None

    def get_remboursement(self, obj):
        lignes = list(obj.remboursements.all())
        if not lignes:
            return None
        if any(r.statut == 'attente_numero' for r in lignes):
            statut = 'attente_numero'
        else:
            statut = 'envoye' if all(r.statut == 'envoye' for r in lignes) else 'en_cours'
        return {'montant': sum(r.montant for r in lignes), 'statut': statut}

    def get_annulation_gratuite(self, obj):
        return obj.arrivee - timezone.now() > tarifs.DELAI_ANNULATION_GRATUITE


class TransfertCreationSerializer(serializers.Serializer):
    aeroport = serializers.PrimaryKeyRelatedField(queryset=AeroportModel.objects.filter(actif=True))
    arrivee = serializers.DateTimeField(help_text="Heure locale d'atterrissage, sans fuseau (ex. 2026-11-02T14:30)")
    numero_vol = serializers.RegexField(r'^[A-Za-z0-9]{2}\s?\d{1,4}[A-Za-z]?$', max_length=10, error_messages={
        'invalid': "Numéro de vol invalide (par exemple AF 520 ou ET935).",
    })
    passagers = serializers.IntegerField(min_value=1, max_value=7)
    bagages = serializers.IntegerField(min_value=0, max_value=10)
    categorie = serializers.ChoiceField(choices=tarifs.CATEGORIE_CHOICES)
    destination = serializers.CharField(max_length=255)
    telephone = serializers.RegexField(r'^\+?[\d\s]{8,20}$', error_messages={
        'invalid': "Indiquez un numéro joignable à l'arrivée, avec l'indicatif (par ex. +33 6 12 34 56 78).",
    })
    message = serializers.CharField(max_length=500, required=False, allow_blank=True)
    reservation = serializers.PrimaryKeyRelatedField(queryset=ReservationModel.objects.all(), required=False, allow_null=True)

    def validate_numero_vol(self, valeur):
        return valeur.replace(' ', '').upper()

    def validate_reservation(self, valeur):
        if valeur and valeur.guest_id != self.context['request'].user.id:
            raise serializers.ValidationError("Réservation introuvable.")
        return valeur

    def validate(self, data):
        # The typed time is the ticket's, in the airport's time zone
        arrivee = data['arrivee']
        naive = timezone.make_naive(arrivee) if timezone.is_aware(arrivee) else arrivee
        data['arrivee'] = services.heure_locale(data['aeroport'], naive)
        return data


def _arrivee(aeroport, brut: str):
    try:
        return services.heure_locale(aeroport, datetime.fromisoformat(brut).replace(tzinfo=None))
    except (TypeError, ValueError):
        return None


class AeroportsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        aeroports = AeroportModel.objects.filter(actif=True, tarifs__actif=True).distinct().prefetch_related('tarifs')
        return Response(AeroportSerializer(aeroports, many=True).data)


class DevisView(APIView):
    """GET ?aeroport=LFW&arrivee=2026-11-02T23:30&passagers=2&bagages=3 → vehicles and prices."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        q = request.query_params
        aeroport = AeroportModel.objects.filter(pk=q.get('aeroport', '').upper(), actif=True).first()
        if not aeroport:
            return Response({'detail': 'Aéroport inconnu.'}, status=status.HTTP_400_BAD_REQUEST)
        arrivee = _arrivee(aeroport, q.get('arrivee', ''))
        if not arrivee:
            return Response({'detail': "Heure d'arrivée invalide."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            passagers, bagages = int(q.get('passagers', 1)), int(q.get('bagages', 0))
        except ValueError:
            return Response({'detail': 'Nombre de passagers ou de bagages invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'options': services.devis(aeroport, arrivee, passagers, bagages),
            'trop_tard': arrivee - timezone.now() < tarifs.DELAI_MIN_RESERVATION,
            'delai_min_heures': int(tarifs.DELAI_MIN_RESERVATION.total_seconds() // 3600),
            'attente_incluse_minutes': tarifs.ATTENTE_INCLUSE_MINUTES,
        })


def _du_voyageur(pk, user):
    return (TransfertModel.objects.select_related('aeroport', 'chauffeur')
            .prefetch_related('paiements', 'remboursements').filter(pk=pk, voyageur=user).first())


class TransfertsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (TransfertModel.objects.filter(voyageur=request.user).select_related('aeroport', 'chauffeur')
              .prefetch_related('paiements', 'remboursements'))
        reservation = request.query_params.get('reservation')
        if reservation:
            try:
                qs = qs.filter(reservation_id=uuid.UUID(reservation))
            except ValueError:
                return Response({'reservation': ['Identifiant invalide.']}, status=status.HTTP_400_BAD_REQUEST)
        data = TransfertSerializer(qs, many=True).data
        return Response({'results': data, 'count': len(data)})

    def post(self, request):
        verifier_ouverture()
        serializer = TransfertCreationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            transfert = services.creer(voyageur=request.user, **serializer.validated_data)
        except services.TransfertErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TransfertSerializer(transfert).data, status=status.HTTP_201_CREATED)


class TransfertView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        transfert = _du_voyageur(pk, request.user)
        if not transfert:
            return Response({'detail': 'Transfert introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        # Return page after payment: the transaction is read again at the provider
        dernier = transfert.paiements.order_by('-cree_le').first()
        if dernier and dernier.statut == 'en_attente':
            paiements.synchroniser_paiement(dernier)
            transfert = _du_voyageur(pk, request.user)
        return Response(TransfertSerializer(transfert).data)

    def delete(self, request, pk):
        transfert = _du_voyageur(pk, request.user)
        if not transfert:
            return Response({'detail': 'Transfert introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            rembourse = services.annuler(transfert, par='voyageur')
        except services.TransfertErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        numero_requis = transfert.remboursements.filter(statut='attente_numero').exists()
        return Response({'detail': 'Transfert annulé.', 'rembourse': rembourse, 'numero_requis': numero_requis})


class PayerTransfertView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        verifier_ouverture()
        transfert = _du_voyageur(pk, request.user)
        if not transfert:
            return Response({'detail': 'Transfert introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            url = services.demarrer_paiement(transfert, request.data.get('moyen') or transfert.moyen)
        except paiements.PaiementErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'url': url})


class CompteRemboursementTransfertView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        transfert = _du_voyageur(pk, request.user)
        if not transfert:
            return Response({'detail': 'Transfert introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CompteRemboursementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not paiements.indiquer_numero_remboursement(transfert, **serializer.validated_data):
            return Response({'detail': "Aucun remboursement n'attend de numéro pour ce transfert."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Numéro enregistré : le remboursement va être envoyé.'})
