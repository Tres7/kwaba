"""Back-office: Kwa-Ba Give (partner NGOs, projects, transfers with proof, donations)."""
import uuid

from django.core.files.base import ContentFile
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.give import services
from apps.give.models import DonModel, OrganisationModel, ProjetModel, ReversementModel
from apps.securite.audit import journaliser
from apps.securite.permissions import EstAdministrateur
from apps.verifications.fichiers import FichierInvalide, piece_identite

from .commun import ChampPhoto, FicheAdmin, ListeAdmin
from .views import _nom, _paginer


# --- ONG -----------------------------------------------------------------------------------------

class OrganisationSerializer(serializers.ModelSerializer):
    logo = ChampPhoto(required=False, allow_null=True)
    image = ChampPhoto(required=False, allow_null=True)
    slug = serializers.SlugField(max_length=80, required=False)
    collecte = serializers.IntegerField(read_only=True)
    nb_dons = serializers.IntegerField(read_only=True)
    nb_projets = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrganisationModel
        fields = ['id', 'nom', 'slug', 'cause', 'pays', 'ville', 'resume', 'description', 'logo', 'image', 'site_web',
                  'numero_enregistrement', 'verifiee_le', 'verification', 'contact_nom', 'contact_email',
                  'contact_telephone', 'coordonnees_reversement', 'actif', 'collecte', 'nb_dons', 'nb_projets']

    def validate(self, data):
        if not self.instance and not data.get('slug'):
            # Page address derived from the name: /give/ecoles-du-mono
            base, n = slugify(data.get('nom', ''))[:70] or 'ong', 1
            slug = base
            while OrganisationModel.objects.filter(slug=slug).exists():
                n += 1
                slug = f"{base}-{n}"
            data['slug'] = slug
        # Published (verification date): what was verified is shown on the site, it must be filled in
        verifiee = data.get('verifiee_le', getattr(self.instance, 'verifiee_le', None))
        verification = data.get('verification', getattr(self.instance, 'verification', ''))
        if verifiee and not verification.strip():
            raise serializers.ValidationError({'verification': ["Indiquez ce qui a été vérifié avant de publier l'ONG."]})
        return data


def _organisations():
    return OrganisationModel.objects.annotate(
        collecte=Sum('dons__montant_ong', filter=Q(dons__statut='paye'), default=0),
        nb_dons=Count('dons', filter=Q(dons__statut='paye'), distinct=True),
        nb_projets=Count('projets', distinct=True),
    ).order_by('nom')


class OrganisationsView(ListeAdmin):
    nom_objet = "ong"
    serializer_class = OrganisationSerializer

    def get_queryset(self):
        return _organisations()


class OrganisationView(FicheAdmin):
    nom_objet = "ong"
    serializer_class = OrganisationSerializer

    def get_queryset(self):
        return _organisations()


# --- Projets -------------------------------------------------------------------------------------

class ProjetSerializer(serializers.ModelSerializer):
    image = ChampPhoto(required=False, allow_null=True)

    class Meta:
        model = ProjetModel
        fields = ['id', 'organisation', 'titre', 'cause', 'resume', 'description', 'lieu', 'objectif', 'image', 'actif']
        read_only_fields = ['organisation']


class ProjetsView(ListeAdmin):
    """Projects of an NGO."""
    nom_objet = "projet"
    serializer_class = ProjetSerializer

    def get_queryset(self):
        return ProjetModel.objects.filter(organisation_id=self.kwargs['pk']).order_by('-cree_le')

    def perform_create(self, serializer):
        organisation = OrganisationModel.objects.get(pk=self.kwargs['pk'])
        projet = serializer.save(organisation=organisation)
        journaliser("backoffice_creation", self.request, utilisateur=self.request.user, objet="projet",
                    id=str(projet.pk), libelle=projet.titre)


class ProjetView(FicheAdmin):
    nom_objet = "projet"
    serializer_class = ProjetSerializer
    queryset = ProjetModel.objects.all()


# --- Reversements --------------------------------------------------------------------------------

def _reversement(r: ReversementModel, request) -> dict:
    return {
        'id': str(r.id), 'reference': r.reference, 'organisation': {'id': str(r.organisation_id), 'nom': r.organisation.nom},
        'coordonnees_reversement': r.organisation.coordonnees_reversement, 'periode': r.periode, 'montant': r.montant,
        'nb_dons': r.nb_dons, 'date_prevue': r.date_prevue, 'statut': r.statut, 'statut_libelle': r.get_statut_display(),
        'moyen': r.moyen, 'reference_operation': r.reference_operation, 'note': r.note, 'effectue_le': r.effectue_le,
        'justificatif': request.build_absolute_uri(r.justificatif.url) if r.justificatif else None,
    }


class ReversementsView(APIView):
    """Transfers, the oldest to make first. Filter: status."""
    permission_classes = [EstAdministrateur]

    def get(self, request):
        qs = ReversementModel.objects.select_related('organisation').order_by('statut', 'date_prevue')
        if (statut := request.query_params.get('statut')) in dict(ReversementModel.STATUTS):
            qs = qs.filter(statut=statut)
        return _paginer(request, qs, lambda r: _reversement(r, request))


class ReversementsPreparerView(APIView):
    """Attaches the donations of finished months to their transfers right away (the worker does it every day)."""
    permission_classes = [EstAdministrateur]

    def post(self, request):
        n = services.preparer_reversements()
        journaliser("backoffice_modification", request, utilisateur=request.user, objet="reversements",
                    operation="preparation", dons=n)
        return Response({'dons': n})


class EffectuerSerializer(serializers.Serializer):
    moyen = serializers.ChoiceField(choices=ReversementModel.MOYENS)
    reference_operation = serializers.CharField(max_length=80)
    effectue_le = serializers.DateField(required=False)
    note = serializers.CharField(required=False, allow_blank=True, default='')
    justificatif = serializers.FileField()


class ReversementEffectuerView(APIView):
    """The transfer is made: proof (PDF or image, published on the NGO's page), method, reference, public message."""
    permission_classes = [EstAdministrateur]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        r = ReversementModel.objects.select_related('organisation').filter(pk=pk).first()
        if not r:
            return Response({'detail': 'Reversement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if r.statut == 'effectue':
            return Response({'detail': 'Ce reversement est déjà effectué.'}, status=status.HTTP_400_BAD_REQUEST)
        donnees = EffectuerSerializer(data=request.data)
        donnees.is_valid(raise_exception=True)
        d = donnees.validated_data
        if d.get('effectue_le') and d['effectue_le'] > timezone.localdate():
            return Response({'effectue_le': ["La date du virement ne peut pas être dans le futur."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Checked (real image or real PDF), image re-encoded without metadata
            contenu, extension, _ = piece_identite(d['justificatif'])
        except FichierInvalide as exc:
            return Response({'justificatif': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        r.justificatif.save(f"{r.reference}.{extension}", ContentFile(contenu.read()), save=False)
        r.note = d['note']
        r.save(update_fields=['justificatif', 'note'])
        services.marquer_effectue(r, moyen=d['moyen'], reference_operation=d['reference_operation'],
                                  effectue_le=d.get('effectue_le'))
        journaliser("backoffice_modification", request, utilisateur=request.user, objet="reversement", id=str(r.pk),
                    libelle=r.reference, operation="effectue", montant=r.montant, ong=r.organisation.nom)
        return Response(_reversement(ReversementModel.objects.select_related('organisation').get(pk=pk), request))


# --- Dons (lecture seule) ------------------------------------------------------------------------

def _don(d: DonModel) -> dict:
    return {
        'id': str(d.id), 'reference': d.reference,
        'donateur': {'nom': _nom(d.donateur), 'email': d.donateur.email},
        'organisation': d.organisation.nom, 'projet': d.projet.titre if d.projet_id else None,
        'montant': d.montant, 'total': d.total, 'montant_ong': d.montant_ong, 'moyen': d.moyen,
        'statut': d.statut, 'statut_libelle': d.get_statut_display(), 'paye_le': d.paye_le, 'cree_le': d.cree_le,
    }


class DonsView(APIView):
    """Donations, most recent first. Filters: status, organisation, q (donor's email)."""
    permission_classes = [EstAdministrateur]

    def get(self, request):
        qs = DonModel.objects.select_related('donateur', 'organisation', 'projet').order_by('-cree_le')
        params = request.query_params
        if (statut := params.get('statut')) in dict(DonModel.STATUTS):
            qs = qs.filter(statut=statut)
        if organisation := params.get('organisation'):
            try:
                qs = qs.filter(organisation_id=uuid.UUID(organisation))
            except ValueError:
                return Response({'organisation': ['Identifiant invalide.']}, status=status.HTTP_400_BAD_REQUEST)
        if q := params.get('q', '').strip():
            qs = qs.filter(donateur__email__icontains=q)
        return _paginer(request, qs, _don)
