"""Opening waiting list: while no listing is published, visitors leave their email."""
import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config import prelancement
from apps.notifications.api import send_mail
from apps.securite.audit import journaliser
from apps.securite.limites import limite_ip
from apps.securite.permissions import EstAdministrateur

from .models import HebergementModel, InscriptionLancementModel

logger = logging.getLogger('apps.hebergements')
MAX_ENVOIS = 500  # per click: beyond that, the administrator starts the sending again


class InscriptionSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    langue = serializers.ChoiceField(choices=['fr', 'en'], default='fr')


class InscriptionLancementView(APIView):
    """GET: pre-launch mode on or off. POST {email, langue}: be notified of the opening. Same response if the
    address is already signed up."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_throttles(self):
        # Only sign-ups are limited; the status is read by every page of the site
        return [limite_ip('lancement', 10, 3600)()] if self.request.method == 'POST' else []

    def get(self, request):
        return Response({'prelancement': prelancement.actif()})

    def post(self, request):
        donnees = InscriptionSerializer(data=request.data)
        donnees.is_valid(raise_exception=True)
        InscriptionLancementModel.objects.get_or_create(email=donnees.validated_data['email'].lower(),
                                                        defaults={'langue': donnees.validated_data['langue']})
        return Response({'inscrit': True}, status=status.HTTP_201_CREATED)


class LancementAdminView(APIView):
    """GET: number of sign-ups (to notify / notified). POST: sends the opening email to the sign-ups not notified yet,
    only if at least one listing is published."""
    permission_classes = [EstAdministrateur]

    def get(self, request):
        qs = InscriptionLancementModel.objects
        return Response({'inscrits': qs.count(), 'a_prevenir': qs.filter(prevenu_le__isnull=True).count(),
                         'logements_publies': HebergementModel.objects.publiees().count()})

    def post(self, request):
        if not HebergementModel.objects.publiees().exists():
            return Response({'detail': "Aucun logement n'est encore publié : les inscrits seront prévenus à l'ouverture."},
                            status=status.HTTP_409_CONFLICT)
        lien = f"{settings.FRONTEND_URL.rstrip('/')}/recherche"
        envoyes = 0
        for inscription in InscriptionLancementModel.objects.filter(prevenu_le__isnull=True).order_by('cree_le')[:MAX_ENVOIS]:
            sujet = "Kwa-Ba: places to stay are now online" if inscription.langue == 'en' else "Kwa-Ba : les logements sont en ligne"
            try:
                send_mail(sujet, render_to_string('emails/hebergements/ouverture.txt', {'langue': inscription.langue, 'lien': lien}),
                          settings.DEFAULT_FROM_EMAIL, [inscription.email])
            except Exception:
                logger.exception("Email d'ouverture non envoyé")
                continue
            inscription.prevenu_le = timezone.now()
            inscription.save(update_fields=['prevenu_le'])
            envoyes += 1
        journaliser('backoffice_modification', request, utilisateur=request.user, objet='lancement', champs=['prevenir'], envoyes=envoyes)
        return Response({'envoyes': envoyes, 'a_prevenir': InscriptionLancementModel.objects.filter(prevenu_le__isnull=True).count()})
