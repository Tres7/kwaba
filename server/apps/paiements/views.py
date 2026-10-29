import json
import logging

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.securite.audit import journaliser

from . import fedapay, paypal, services, tarifs
from .models import ProfilVersementModel, VersementModel
from .operateurs import PAYS, operateurs_ouverts, pays_ouverts

logger = logging.getLogger('apps.paiements')


class ConfigView(APIView):
    """What the frontend needs to know to display the payment (public)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            'actif': services.paiement_actif(),
            # Methods offered to the traveller: mobile_money and carte (FedaPay), paypal (in euros)
            'moyens': services.moyens_actifs(),
            'fcfa_par_euro': float(paypal.FCFA_PAR_EURO),
            'environnement': settings.FEDAPAY['ENV'],
            'frais_voyageur': float(tarifs.FRAIS_VOYAGEUR),
            'frais_reduits': float(tarifs.FRAIS_REDUITS),
            'commission_hote': float(tarifs.COMMISSION_HOTE),
            'commissions': {'particulier': float(tarifs.COMMISSION_PARTICULIER), 'hotel': float(tarifs.COMMISSION_HOTEL),
                            'fondateur': float(tarifs.COMMISSION_FONDATEUR)},
            'delai_paiement_minutes': settings.FEDAPAY['EXPIRATION_MINUTES'],
            'pays': [
                {'code': code, 'nom': p['nom'], 'indicatif': p['indicatif'], 'chiffres': p['chiffres'],
                 'operateurs': [{'code': c, 'nom': n} for c, n in p['operateurs']]}
                for code, p in pays_ouverts().items()
            ],
        })


@method_decorator(csrf_exempt, name='dispatch')
class WebhookFedaPayView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        corps = request.body
        secret = settings.FEDAPAY['WEBHOOK_SECRET']
        if not secret and not settings.DEBUG:
            # Without a secret, anyone could call this endpoint: refused outside development
            logger.error("Webhook FedaPay refusé : FEDAPAY_WEBHOOK_SECRET n'est pas configurée")
            journaliser('webhook_refuse', request, motif='secret_absent')
            return Response({'detail': 'Webhook non configuré.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if secret and not fedapay.signature_valide(corps, request.headers.get('X-FEDAPAY-SIGNATURE', ''), secret):
            logger.warning("Webhook FedaPay rejeté : signature invalide")
            journaliser('webhook_refuse', request, motif='signature_invalide')
            return Response({'detail': 'Signature invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            evenement = json.loads(corps or b'{}')
        except ValueError:
            return Response({'detail': 'Corps invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            services.traiter_evenement(evenement)
        except Exception:
            # 500: FedaPay will send the event again later
            logger.exception("Erreur pendant le traitement du webhook %s", evenement.get('name'))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'recu': True})


# --- Host --------------------------------------------------------------------------------

class EstHote(IsAuthenticated):
    message = "Réservé aux hôtes."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in ('hote', 'admin')


def _valider_compte(data):
    """Operator available in the country, number with the right number of digits."""
    pays = data['pays']
    if data['operateur'] not in operateurs_ouverts(pays):
        raise serializers.ValidationError({'operateur': "Cet opérateur n'est pas disponible dans le pays choisi."})
    attendu = PAYS[pays]['chiffres']
    if len(data['numero']) != attendu:
        raise serializers.ValidationError({'numero': f"Le numéro doit comporter {attendu} chiffres (sans l'indicatif +{PAYS[pays]['indicatif']})."})
    return data


def _chiffres(valeur: str) -> str:
    return ''.join(c for c in valeur if c.isdigit())


class CompteRemboursementSerializer(serializers.Serializer):
    pays = serializers.ChoiceField(choices=list(PAYS))
    operateur = serializers.CharField(max_length=30)
    numero = serializers.CharField(max_length=20)

    def validate_numero(self, valeur):
        return _chiffres(valeur)

    def validate(self, data):
        return _valider_compte(data)


class ProfilVersementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfilVersementModel
        fields = ['pays', 'operateur', 'numero', 'titulaire', 'mis_a_jour_le']
        read_only_fields = ['mis_a_jour_le']

    def validate_numero(self, valeur):
        return _chiffres(valeur)

    def validate_titulaire(self, valeur):
        valeur = ' '.join(valeur.split())
        if len(valeur) < 3:
            raise serializers.ValidationError("Indiquez le nom complet du titulaire du compte.")
        return valeur

    def validate(self, data):
        return _valider_compte(data)


class ProfilVersementView(APIView):
    permission_classes = [EstHote]

    def get(self, request):
        profil = ProfilVersementModel.objects.filter(hote_id=request.user.pk).first()
        return Response(ProfilVersementSerializer(profil).data if profil else None)

    def put(self, request):
        profil = ProfilVersementModel.objects.filter(hote_id=request.user.pk).first()
        serializer = ProfilVersementSerializer(profil, data=request.data)
        serializer.is_valid(raise_exception=True)
        ancien = (profil.operateur, profil.numero) if profil else None
        serializer.save(hote_id=request.user.pk)
        if ancien != (serializer.instance.operateur, serializer.instance.numero):
            # Changing the account that receives the money is the action targeted after an account takeover: it is logged
            journaliser('profil_versement_modifie', request, utilisateur=request.user,
                        operateur=serializer.instance.operateur, numero_fin=serializer.instance.numero[-2:])
        # Payouts blocked for lack of a profile start again at the next pass of the worker
        VersementModel.objects.filter(hote_id=request.user.pk, statut__in=('planifie', 'echoue')).update(
            statut='planifie', derniere_erreur='', tentatives=0,
        )
        return Response(serializer.data)


def _type_partenaire(hote) -> str:
    """particulier, hotel or fondateur (Founders Programme ongoing): set in the back-office."""
    conditions = tarifs.conditions(hote)
    if conditions and conditions.categorie == 'hotel':
        return 'hotel'
    if conditions and conditions.fondateur_le(timezone.localdate()):
        return 'fondateur'
    return 'particulier'


class RevenusView(APIView):
    permission_classes = [EstHote]

    def get(self, request):
        versements = (
            VersementModel.objects.filter(hote_id=request.user.pk)
            .exclude(statut='annule')
            .order_by('-date_prevue')
        )

        from apps.hebergements import api as hebergements  # local imports: these modules depend on paiements
        from apps.reservations import api as reservations

        derniers = list(versements[:200])
        sejours = reservations.objets(v.reservation_id for v in derniers)
        annonces = hebergements.resumes({r.hebergement_id for r in sejours.values()})

        def total(*statuts):
            return versements.filter(statut__in=statuts).aggregate(s=Sum('montant'))['s'] or 0

        return Response({
            'totaux': {
                'a_venir': total('planifie', 'echoue'),
                'en_cours': total('en_cours'),
                'verse': total('envoye'),
                'commission': versements.aggregate(s=Sum('commission'))['s'] or 0,
            },
            'profil_complet': ProfilVersementModel.objects.filter(hote_id=request.user.pk).exists(),
            # This host's commission rate today (8 %, 12 % for a hotel, 5 % during the Founders Programme)
            'commission_pourcent': float(tarifs.taux_commission(request.user) * 100),
            # Partner type saved by the team (never editable by the host) and traveller's fee rate
            'partenaire': _type_partenaire(request.user),
            'frais_voyageur_pourcent': float(tarifs.FRAIS_VOYAGEUR * 100),
            'versements': [
                {
                    'id': str(v.id),
                    'reservation_id': str(v.reservation_id),
                    'reference': sejours[v.reservation_id].reference,
                    'hebergement': annonces.get(sejours[v.reservation_id].hebergement_id, {}).get('name', ''),
                    'voyageur': sejours[v.reservation_id].guest.get_full_name() if sejours[v.reservation_id].guest else '',
                    'check_in': sejours[v.reservation_id].check_in,
                    'check_out': sejours[v.reservation_id].check_out,
                    'montant_brut': v.montant_brut,
                    'commission': v.commission,
                    'montant': v.montant,
                    'statut': v.statut,
                    'date_prevue': v.date_prevue,
                    'envoye_le': v.envoye_le,
                    'probleme': v.derniere_erreur if v.statut in ('planifie', 'echoue') else '',
                }
                for v in derniers if v.reservation_id in sejours
            ],
        })
