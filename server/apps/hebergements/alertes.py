"""Availability alerts: "notify me if these dates become free" on a full listing.

The places where dates can become free (cancellation, expired payment, closure reopened, more units, new or
reactivated type) call signaler_liberation(). It only sets a flag once the transaction is committed: the worker
(apps.paiements.services.passe) checks the flagged alerts and sends the emails, never during a web request.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.securite.limites import limite_ip

from . import stock
from .models import AlerteDisponibiliteModel, HebergementModel, TypeLogementModel

logger = logging.getLogger('apps.hebergements')

MAX_NUITS = 60
MAX_ALERTES_PAR_EMAIL = 20
# A visitor who never confirms their address: the alert is dropped after this delay
DELAI_CONFIRMATION = timedelta(days=7)
OUVERTES = ('a_confirmer', 'active')


def signaler_liberation(hebergement_id, debut=None, fin=None) -> None:
    """Dates of the listing may have become bookable again (over [debut, fin), or anywhere if not given)."""
    def marquer():
        alertes = AlerteDisponibiliteModel.objects.filter(hebergement_id=hebergement_id, statut='active')
        if debut and fin:
            alertes = alertes.filter(date_debut__lt=fin, date_fin__gt=debut)
        alertes.update(a_verifier=True)

    transaction.on_commit(marquer)


def _disponible(alerte) -> bool:
    if alerte.type_logement_id:
        types = [alerte.type_logement] if alerte.type_logement.actif else []
    else:
        types = list(TypeLogementModel.objects.filter(hebergement_id=alerte.hebergement_id, actif=True))
    return any(stock.est_disponible(t, alerte.date_debut, alerte.date_fin, alerte.nb_unites) for t in types)


class AlerteSerializer(serializers.Serializer):
    debut = serializers.DateField()
    fin = serializers.DateField()
    type_logement = serializers.UUIDField(required=False, allow_null=True)
    nb_unites = serializers.IntegerField(min_value=1, max_value=20, default=1)
    email = serializers.EmailField(max_length=254, required=False)
    langue = serializers.ChoiceField(choices=['fr', 'en'], default='fr')

    def validate(self, data):
        aujourd_hui = timezone.localdate()
        if data['debut'] < aujourd_hui:
            raise serializers.ValidationError({'debut': "La date d'arrivée est passée."})
        if data['fin'] <= data['debut']:
            raise serializers.ValidationError({'fin': "Le départ doit suivre l'arrivée."})
        if (data['fin'] - data['debut']).days > MAX_NUITS:
            raise serializers.ValidationError({'fin': f"{MAX_NUITS} nuits au plus."})
        if data['debut'] > aujourd_hui + timedelta(days=540):
            raise serializers.ValidationError({'debut': "Date trop lointaine."})
        return data


class AlerteCreateView(APIView):
    """POST {debut, fin, type_logement?, nb_unites?, email?, langue}: be notified if these dates become free.

    Signed in: active at once, sent to the account's address. Without an account: `email` required, and the alert
    waits for the address to be confirmed (link emailed by the worker).
    """
    permission_classes = [AllowAny]
    throttle_classes = [limite_ip('alerte_disponibilite', 10, 3600)]

    def post(self, request, pk):
        hebergement = HebergementModel.objects.publiees().filter(pk=pk).first()
        if hebergement is None:
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        donnees = AlerteSerializer(data=request.data)
        donnees.is_valid(raise_exception=True)
        d = donnees.validated_data

        type_logement = None
        if d.get('type_logement'):
            type_logement = TypeLogementModel.objects.filter(pk=d['type_logement'], hebergement=hebergement, actif=True).first()
            if type_logement is None:
                return Response({'type_logement': ['Type de logement inconnu.']}, status=status.HTTP_400_BAD_REQUEST)

        connecte = request.user.is_authenticated
        email = request.user.email if connecte else d.get('email', '')
        if not email:
            return Response({'email': ['Indiquez votre adresse email.']}, status=status.HTTP_400_BAD_REQUEST)
        email = email.strip().lower()

        alerte = AlerteDisponibiliteModel(hebergement=hebergement, type_logement=type_logement, date_debut=d['debut'],
                                          date_fin=d['fin'], nb_unites=d['nb_unites'])
        if _disponible(alerte):
            return Response({'detail': "Ces dates sont disponibles : vous pouvez réserver dès maintenant.", 'code': 'disponible'},
                            status=status.HTTP_409_CONFLICT)

        ouvertes = AlerteDisponibiliteModel.objects.filter(email=email, statut__in=OUVERTES)
        existante = ouvertes.filter(hebergement=hebergement, type_logement=type_logement, date_debut=d['debut'],
                                    date_fin=d['fin']).first()
        if existante is None:
            if ouvertes.count() >= MAX_ALERTES_PAR_EMAIL:
                return Response({'detail': f"Vous avez déjà {MAX_ALERTES_PAR_EMAIL} alertes en cours."},
                                status=status.HTTP_400_BAD_REQUEST)
            alerte.email, alerte.langue = email, d['langue']
            alerte.utilisateur = request.user if connecte else None
            alerte.statut = 'active' if connecte else 'a_confirmer'
            alerte.save()
        elif connecte and existante.statut == 'a_confirmer':
            # Signed in with this address: no need to confirm it by email
            existante.statut, existante.utilisateur = 'active', request.user
            existante.save(update_fields=['statut', 'utilisateur'])
        # Same answer whether the alert existed or not: nothing is revealed about an address
        return Response({'statut': 'active' if connecte else 'a_confirmer', 'email': email}, status=status.HTTP_201_CREATED)


class JetonSerializer(serializers.Serializer):
    jeton = serializers.CharField(max_length=64)


def _par_jeton(request):
    donnees = JetonSerializer(data=request.data)
    donnees.is_valid(raise_exception=True)
    return AlerteDisponibiliteModel.objects.select_related('hebergement').filter(jeton=donnees.validated_data['jeton']).first()


def _resume(alerte) -> dict:
    return {'statut': alerte.statut, 'hebergement': alerte.hebergement.name, 'hebergement_id': str(alerte.hebergement_id),
            'debut': alerte.date_debut, 'fin': alerte.date_fin}


class AlerteConfirmationView(APIView):
    """POST {jeton}: confirms the address of an alert created without an account (link of the email)."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [limite_ip('alerte_jeton', 30, 3600)]

    def post(self, request):
        alerte = _par_jeton(request)
        if alerte is None:
            return Response({'detail': "Ce lien n'est plus valable."}, status=status.HTTP_404_NOT_FOUND)
        if alerte.statut == 'a_confirmer':
            # Dates may have become free since the request: checked at the next pass
            alerte.statut, alerte.a_verifier = 'active', True
            alerte.save(update_fields=['statut', 'a_verifier'])
        return Response(_resume(alerte))


class AlerteDesinscriptionView(APIView):
    """POST {jeton}: stops the alert (link of every alert email)."""
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [limite_ip('alerte_jeton', 30, 3600)]

    def post(self, request):
        alerte = _par_jeton(request)
        if alerte is None:
            return Response({'detail': "Ce lien n'est plus valable."}, status=status.HTTP_404_NOT_FOUND)
        if alerte.statut in OUVERTES:
            alerte.statut = 'annulee'
            alerte.save(update_fields=['statut'])
        return Response(_resume(alerte))


# --- Worker ---

def _url(alerte, chemin: str) -> str:
    prefixe = '/en' if alerte.langue == 'en' else ''
    return f"{settings.FRONTEND_URL.rstrip('/')}{prefixe}{chemin}"


def _date(alerte, jour) -> str:
    if alerte.langue == 'en':
        return f"{jour.strftime('%B')} {jour.day}, {jour.year}"
    from apps.paiements.notifications import _date as date_fr  # local import: paiements depends on hebergements
    return date_fr(jour)


def _contexte(alerte) -> dict:
    return {
        'langue': alerte.langue, 'hebergement': alerte.hebergement.name, 'ville': alerte.hebergement.city,
        'type_logement': alerte.type_logement.nom if alerte.type_logement_id else '',
        'arrivee': _date(alerte, alerte.date_debut), 'depart': _date(alerte, alerte.date_fin),
        'url_desinscription': _url(alerte, f"/alertes?desinscrire={alerte.jeton}"),
    }


def envoyer_confirmation(alerte):
    from apps.paiements.notifications import _envoyer
    sujet = "Confirm your Kwa-Ba alert" if alerte.langue == 'en' else "Confirmez votre alerte Kwa-Ba"
    _envoyer('emails/hebergements/alerte_confirmation.txt', sujet, [alerte.email], {
        **_contexte(alerte), 'url_confirmation': _url(alerte, f"/alertes?confirmer={alerte.jeton}"),
    })


def envoyer_disponible(alerte):
    from apps.paiements.notifications import _envoyer
    h = alerte.hebergement
    sujet = f"Dates available again: {h.name}" if alerte.langue == 'en' else f"Des dates se sont libérées : {h.name}"
    lien = f"/hebergements/{h.id}?check_in={alerte.date_debut}&check_out={alerte.date_fin}"
    if alerte.type_logement_id:
        lien += f"&type={alerte.type_logement_id}&unites={alerte.nb_unites}"
    _envoyer('emails/hebergements/alerte_disponible.txt', sujet, [alerte.email], {**_contexte(alerte), 'url': _url(alerte, lien)})


def passe() -> dict:
    """Expires the old alerts, sends the confirmation links and the "dates available again" emails."""
    aujourd_hui = timezone.localdate()
    ouvertes = AlerteDisponibiliteModel.objects.filter(statut__in=OUVERTES)
    expirees = ouvertes.filter(date_debut__lt=aujourd_hui).update(statut='expiree', a_verifier=False)
    expirees += AlerteDisponibiliteModel.objects.filter(
        statut='a_confirmer', cree_le__lt=timezone.now() - DELAI_CONFIRMATION).update(statut='expiree')

    relations = ('hebergement', 'type_logement')
    confirmations = 0
    for alerte in AlerteDisponibiliteModel.objects.filter(statut='a_confirmer', confirmation_envoyee=False).select_related(*relations)[:50]:
        try:
            envoyer_confirmation(alerte)
        except Exception:
            logger.exception("Lien de confirmation d'alerte non envoyé (%s), nouvel essai à la prochaine passe", alerte.pk)
            continue
        AlerteDisponibiliteModel.objects.filter(pk=alerte.pk).update(confirmation_envoyee=True)
        confirmations += 1

    prevenus = 0
    publiees = HebergementModel.objects.publiees().values('pk')
    for alerte in AlerteDisponibiliteModel.objects.filter(statut='active', a_verifier=True).select_related(*relations)[:200]:
        if not (HebergementModel.objects.filter(pk=alerte.hebergement_id, pk__in=publiees).exists() and _disponible(alerte)):
            AlerteDisponibiliteModel.objects.filter(pk=alerte.pk).update(a_verifier=False)
            continue
        try:
            envoyer_disponible(alerte)
        except Exception:
            logger.exception("Alerte de disponibilité non envoyée (%s), nouvel essai à la prochaine passe", alerte.pk)
            continue
        AlerteDisponibiliteModel.objects.filter(pk=alerte.pk).update(statut='notifiee', a_verifier=False, notifiee_le=timezone.now())
        prevenus += 1
    return {'alertes_expirees': expirees, 'alertes_confirmations': confirmations, 'alertes_envoyees': prevenus}
