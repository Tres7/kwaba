"""Document download (traveller, donor, admin) and invoice management in the back-office."""
from django.core.files.base import ContentFile
from django.http import HttpResponse
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.contrats import api as contrats
from apps.securite.audit import journaliser
from apps.securite.backoffice import paginer
from apps.securite.permissions import EstAdministrateur

from . import generateurs, services
from .models import FactureModel, ParametresSocieteModel
from .registre import PRODUITS


def _pdf(contenu: bytes, nom: str) -> HttpResponse:
    reponse = HttpResponse(contenu, content_type='application/pdf')
    reponse['Content-Disposition'] = f'attachment; filename="{nom}"'
    reponse['Cache-Control'] = 'no-store'
    reponse['X-Content-Type-Options'] = 'nosniff'
    return reponse


class DocumentView(APIView):
    """GET /documents/<type>/<id>/<bon|recu|facture>/: reserved for the traveller (or donor) concerned and the admins,
    once the payment is received."""
    permission_classes = [IsAuthenticated]

    def get(self, request, type_objet, pk, document):
        produit = PRODUITS.get(type_objet)
        if not produit or document not in produit.documents:
            return Response({'detail': 'Document inconnu.'}, status=status.HTTP_404_NOT_FOUND)
        objet = produit.charger(pk)
        # Same response if the object does not exist or belongs to someone else: nothing leaks
        if not objet or (produit.proprietaire_id(objet) != request.user.pk and request.user.role != 'admin'):
            return Response({'detail': 'Document introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if not produit.paye(objet):
            return Response({'detail': 'Les documents sont disponibles une fois le paiement reçu.'}, status=status.HTTP_409_CONFLICT)
        reference = produit.reference(objet)
        if document == 'bon':
            return _pdf(produit.bon(objet), f"bon-{reference}.pdf")
        if document == 'recu':
            return _pdf(produit.recu(objet), f"{produit.prefixe_recu}-{reference}.pdf")
        try:
            f = services.facture_de(type_objet, objet)
        except services.DocumentErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        return _pdf(f.pdf.read() if f.pdf else generateurs.facture(f), f"facture-{f.numero}.pdf")


# --- Back-office -----------------------------------------------------------------------------------

class SocieteSerializer(serializers.ModelSerializer):
    complets = serializers.BooleanField(read_only=True)
    signature_presente = serializers.SerializerMethodField()

    class Meta:
        model = ParametresSocieteModel
        fields = ['raison_sociale', 'nom_commercial', 'forme_juridique', 'adresse', 'pays', 'nif', 'rccm', 'telephone',
                  'email', 'site', 'assujetti_tva', 'taux_tva', 'mentions', 'representant_nom', 'representant_qualite',
                  'complets', 'signature_presente']

    def get_signature_presente(self, obj) -> bool:
        return bool(obj.signature_representant)


MAX_SIGNATURE_SCAN = 5 * 1024 * 1024


class SocieteView(APIView):
    """Legal information printed on the documents. PUT as JSON or as multipart with the representative's scanned
    signature (`signature_representant`, light background made transparent); `supprimer_signature=true` removes it."""
    permission_classes = [EstAdministrateur]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        return Response(SocieteSerializer(ParametresSocieteModel.courants()).data)

    def put(self, request):
        societe = ParametresSocieteModel.courants()
        etait_immatriculee = societe.immatriculee
        serializer = SocieteSerializer(societe, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        fichier = request.FILES.get('signature_representant')
        contenu = None
        if fichier:
            if fichier.size > MAX_SIGNATURE_SCAN:
                return Response({'signature_representant': ['Image trop lourde (5 Mo au plus).']}, status=status.HTTP_400_BAD_REQUEST)
            try:
                contenu = contrats.signature_png(fichier.read(), fond_blanc_transparent=True)
            except contrats.ContratErreur as exc:
                return Response({'signature_representant': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        societe = serializer.save()
        if contenu:
            societe.signature_representant.save('signature-representant.png', ContentFile(contenu), save=True)
        elif str(request.data.get('supprimer_signature')).lower() == 'true' and societe.signature_representant:
            societe.signature_representant.delete(save=True)
        journaliser("backoffice_modification", request, utilisateur=request.user, objet="societe", champs=sorted(request.data.keys()))
        if societe.immatriculee and not etait_immatriculee:
            # RCCM and NIF just filled in: hosts are invited to sign their agreement, once
            invites = contrats.inviter_hotes_a_signer()
            journaliser("backoffice_modification", request, utilisateur=request.user, objet="contrats_hotes", invites=invites)
        return Response(SocieteSerializer(societe).data)


class SignatureRepresentantView(APIView):
    """Preview of the saved signature (private storage, read by the API)."""
    permission_classes = [EstAdministrateur]

    def get(self, request):
        societe = ParametresSocieteModel.courants()
        if not societe.signature_representant:
            return Response({'detail': 'Aucune signature.'}, status=status.HTTP_404_NOT_FOUND)
        with societe.signature_representant.open('rb') as f:
            reponse = HttpResponse(f.read(), content_type='image/png')
        reponse['Cache-Control'] = 'no-store'
        return reponse


def _facture(f: FactureModel) -> dict:
    return {'id': str(f.id), 'numero': f.numero, 'emise_le': f.emise_le, 'objet_type': f.objet_type,
            'objet_libelle': f.get_objet_type_display(), 'objet_id': str(f.objet_id) if f.objet_id else None,
            'client_nom': f.client_nom, 'client_email': f.client_email, 'total_ttc': f.total_ttc, 'tva': f.tva}


class LigneSerializer(serializers.Serializer):
    libelle = serializers.CharField(max_length=200)
    quantite = serializers.IntegerField(min_value=1, max_value=10000)
    prix_unitaire = serializers.IntegerField(min_value=0, max_value=1_000_000_000)


class FactureLibreSerializer(serializers.Serializer):
    client_nom = serializers.CharField(max_length=150)
    client_email = serializers.EmailField(required=False, allow_blank=True, default='')
    client_adresse = serializers.CharField(required=False, allow_blank=True, default='')
    lignes = LigneSerializer(many=True, allow_empty=False)


class FacturesView(APIView):
    """GET: issued invoices (q: number, customer). POST: invoice of a paid stay, transfer or rental
    ({objet_type, objet_id}), or free-form invoice ({client_nom, client_email, client_adresse, lignes})."""
    permission_classes = [EstAdministrateur]

    def get(self, request):
        qs = FactureModel.objects.all()
        if q := request.query_params.get('q', '').strip():
            qs = qs.filter(numero__icontains=q) | qs.filter(client_nom__icontains=q) | qs.filter(client_email__icontains=q)
        return paginer(request, qs.order_by('-emise_le'), _facture)

    def post(self, request):
        try:
            produit = PRODUITS.get(request.data.get('objet_type'))
            if produit and produit.facture:
                objet = produit.charger(request.data.get('objet_id')) if request.data.get('objet_id') else None
                if not objet:
                    return Response({'detail': 'Élément introuvable.'}, status=status.HTTP_404_NOT_FOUND)
                f = services.facture_de(produit.type, objet, par=request.user)
            else:
                donnees = FactureLibreSerializer(data=request.data)
                donnees.is_valid(raise_exception=True)
                f = services.facture_libre(**donnees.validated_data, par=request.user)
        except services.DocumentErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)
        journaliser("backoffice_creation", request, utilisateur=request.user, objet="facture", id=str(f.pk), libelle=f.numero)
        return Response(_facture(f), status=status.HTTP_201_CREATED)


class FacturePdfView(APIView):
    permission_classes = [EstAdministrateur]

    def get(self, request, pk):
        f = FactureModel.objects.filter(pk=pk).first()
        if not f:
            return Response({'detail': 'Facture introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return _pdf(f.pdf.read() if f.pdf else generateurs.facture(f), f"facture-{f.numero}.pdf")
