from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.prelancement import verifier_ouverture
from apps.paiements import api as paiements

from . import montants, services
from .models import DonModel, OrganisationModel, ProjetModel, ReversementModel


class ProjetSerializer(serializers.ModelSerializer):
    collecte = serializers.SerializerMethodField()

    class Meta:
        model = ProjetModel
        fields = ['id', 'titre', 'cause', 'resume', 'description', 'lieu', 'objectif', 'image', 'collecte']

    def get_collecte(self, obj):
        return getattr(obj, 'collecte', None) or 0


class ReversementSerializer(serializers.ModelSerializer):
    organisation = serializers.SerializerMethodField()

    class Meta:
        model = ReversementModel
        fields = ['id', 'reference', 'organisation', 'periode', 'montant', 'nb_dons', 'statut', 'date_prevue',
                  'effectue_le', 'moyen', 'reference_operation', 'justificatif', 'note']

    def get_organisation(self, obj):
        return {'nom': obj.organisation.nom, 'slug': obj.organisation.slug}


class OrganisationSerializer(serializers.ModelSerializer):
    impact = serializers.SerializerMethodField()

    class Meta:
        model = OrganisationModel
        fields = ['id', 'nom', 'slug', 'cause', 'pays', 'ville', 'resume', 'logo', 'image', 'impact']

    def get_impact(self, obj):
        return {'collecte': getattr(obj, 'collecte', None) or 0, 'nb_dons': getattr(obj, 'nb_dons', 0)}


class OrganisationDetailSerializer(OrganisationSerializer):
    projets = serializers.SerializerMethodField()
    reversements = serializers.SerializerMethodField()

    class Meta(OrganisationSerializer.Meta):
        fields = OrganisationSerializer.Meta.fields + [
            'description', 'site_web', 'numero_enregistrement', 'verifiee_le', 'verification', 'projets', 'reversements',
        ]

    def get_impact(self, obj):
        return services.impact([obj])

    def get_projets(self, obj):
        projets = obj.projets.filter(actif=True).annotate(collecte=Sum('dons__montant_ong', filter=Q(dons__statut='paye')))
        return ProjetSerializer(projets, many=True, context=self.context).data

    def get_reversements(self, obj):
        return ReversementSerializer(obj.reversements.filter(nb_dons__gt=0), many=True, context=self.context).data


class DonSerializer(serializers.ModelSerializer):
    reference = serializers.CharField(read_only=True)
    organisation = serializers.SerializerMethodField()
    projet = serializers.SerializerMethodField()
    reversement = serializers.SerializerMethodField()
    date_reversement = serializers.SerializerMethodField()

    class Meta:
        model = DonModel
        fields = ['id', 'reference', 'organisation', 'projet', 'montant', 'couvre_frais', 'frais', 'total', 'montant_ong',
                  'moyen', 'partage_identite', 'statut', 'paye_le', 'date_reversement', 'reversement', 'cree_le']

    def get_organisation(self, obj):
        o = obj.organisation
        return {'nom': o.nom, 'slug': o.slug, 'cause': o.cause}

    def get_projet(self, obj):
        return {'id': str(obj.projet_id), 'titre': obj.projet.titre} if obj.projet_id else None

    def get_reversement(self, obj):
        r = obj.reversement
        if not r:
            return None
        return {'reference': r.reference, 'statut': r.statut, 'effectue_le': r.effectue_le,
                'justificatif': self.context['request'].build_absolute_uri(r.justificatif.url) if r.justificatif else None}

    def get_date_reversement(self, obj):
        return montants.date_reversement(timezone.localtime(obj.paye_le).date()) if obj.paye_le else None


class DonCreationSerializer(serializers.Serializer):
    organisation = serializers.SlugRelatedField(slug_field='slug', queryset=services.organisations_publiees())
    projet = serializers.PrimaryKeyRelatedField(queryset=ProjetModel.objects.filter(actif=True), required=False,
                                                allow_null=True)
    montant = serializers.IntegerField(min_value=montants.MONTANT_MIN, max_value=montants.MONTANT_MAX)
    couvre_frais = serializers.BooleanField(default=True)
    moyen = serializers.ChoiceField(choices=[m for m, _ in DonModel.MOYENS])
    partage_identite = serializers.BooleanField(default=False)


def _organisations():
    return services.organisations_publiees().annotate(
        collecte=Sum('dons__montant_ong', filter=Q(dons__statut='paye')),
        nb_dons=Count('dons', filter=Q(dons__statut='paye')),
    )


class ConfigView(APIView):
    """What the donation page must show before payment (public)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            'actif': paiements.paiement_actif(),
            'moyens': paiements.moyens_actifs(),
            'montants_suggeres': montants.MONTANTS_SUGGERES,
            'montant_min': montants.MONTANT_MIN,
            'montant_max': montants.MONTANT_MAX,
            'frais_paiement': float(montants.FRAIS_PAIEMENT),
            'commission_kwaba': float(montants.COMMISSION_KWABA),
            'jour_reversement': montants.JOUR_REVERSEMENT,
            'fcfa_par_euro': float(paiements.FCFA_PAR_EURO),
            'causes': [{'code': code, **c} for code, c in montants.CAUSES.items()],
        })


class OrganisationsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = _organisations()
        cause = request.query_params.get('cause')
        if cause:
            qs = qs.filter(cause=cause)
        data = OrganisationSerializer(qs, many=True, context={'request': request}).data
        return Response({'results': data, 'count': len(data)})


class OrganisationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        organisation = services.organisations_publiees().filter(slug=slug).first()
        if not organisation:
            return Response({'detail': 'Organisation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrganisationDetailSerializer(organisation, context={'request': request}).data)


class ImpactView(APIView):
    """Transparency: amounts collected and transferred, per cause, and proofs of the latest transfers."""
    permission_classes = [AllowAny]

    def get(self, request):
        par_cause = services.impact_par_cause()
        reversements = (ReversementModel.objects.filter(statut='effectue').select_related('organisation')
                        .order_by('-effectue_le')[:20])
        return Response({
            **services.impact(),
            'nb_organisations': services.organisations_publiees().count(),
            'causes': [{'code': code, 'nom': c['nom'], **par_cause.get(code, {'collecte': 0, 'nb_dons': 0})}
                       for code, c in montants.CAUSES.items()],
            'reversements': ReversementSerializer(reversements, many=True, context={'request': request}).data,
        })


def _dons_de(user):
    return DonModel.objects.filter(donateur_id=user.pk).select_related('organisation', 'projet', 'reversement')


class DonsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dons = _dons_de(request.user)
        payes = dons.filter(statut='paye').aggregate(total=Sum('montant'), nb=Count('id'))
        data = DonSerializer(dons.exclude(statut='echoue'), many=True, context={'request': request}).data
        return Response({'results': data, 'count': len(data), 'total_donne': payes['total'] or 0, 'nb_payes': payes['nb']})

    def post(self, request):
        verifier_ouverture()
        serializer = DonCreationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            don, url = services.donner(donateur=request.user, **serializer.validated_data)
        except services.DonErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'id': str(don.id), 'url': url}, status=status.HTTP_201_CREATED)


class DonView(APIView):
    """Return page after payment: reads the payment again at the provider if needed."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        don = _dons_de(request.user).filter(pk=pk).first()
        if not don:
            return Response({'detail': 'Don introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        services.synchroniser(don)
        return Response(DonSerializer(don, context={'request': request}).data)
