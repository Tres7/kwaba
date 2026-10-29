"""Back-office: car hire (rules, owners' vehicles, handover places, owners, follow-up)."""
from django.db import transaction
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.locations import services
from apps.locations.models import (
    CategorieVehiculeModel, LieuRemiseModel, LocationModel, ParametresLocationModel, PartenaireLocationModel,
    PhotoVehiculeModel,
)
from apps.paiements.operateurs import operateurs_du_pays
from apps.transferts import api as transferts
from apps.securite.audit import journaliser
from apps.securite.backoffice import ChampPhoto, FicheAdmin, ListeAdmin
from apps.securite.permissions import EstAdministrateur

from .views import _motif, _nom, _paginer


# --- Rules (a single row) ------------------------------------------------------------------

class ParametresSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParametresLocationModel
        fields = ['commission_pourcent', 'delai_min_jours', 'duree_max_jours', 'annulation_gratuite_heures', 'conditions',
                  'caution_en_ligne', 'restitution_caution_heures']


class ParametresView(APIView):
    """GET: rules in force (null while they do not exist: rental is then not offered). PUT: set them."""
    permission_classes = [EstAdministrateur]

    def get(self, request):
        params = ParametresLocationModel.objects.first()
        return Response(ParametresSerializer(params).data if params else None)

    def put(self, request):
        params = ParametresLocationModel.objects.first()
        serializer = ParametresSerializer(params, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        journaliser("backoffice_modification", request, utilisateur=request.user, objet="regles_location",
                    champs=sorted(request.data.keys()))
        return Response(serializer.data)


# --- Reference lists --------------------------------------------------------------------------------

class PhotoVehiculeSerializer(serializers.ModelSerializer):
    url = ChampPhoto(source='image', read_only=True)

    class Meta:
        model = PhotoVehiculeModel
        fields = ['id', 'url']


class CategorieSerializer(serializers.ModelSerializer):
    # Photos handled one by one (PhotosCategorieView): several photos in a single request would exceed
    # the maximum size accepted by nginx
    photos = PhotoVehiculeSerializer(many=True, read_only=True)

    class Meta:
        model = CategorieVehiculeModel
        fields = ['id', 'nom', 'gamme', 'exemple_modele', 'description', 'places', 'bagages', 'boite', 'carburant',
                  'climatisation', 'photos', 'proprietaire', 'prix_jour', 'sans_chauffeur', 'avec_chauffeur', 'caution_jours',
                  'caution', 'immatriculation', 'annee', 'assurance_fin', 'visite_technique_fin', 'actif', 'ordre']
        read_only_fields = ['caution']

    def validate(self, data):
        def valeur(champ, defaut=None):
            return data.get(champ, getattr(self.instance, champ, defaut))

        if valeur('actif', False):
            if not valeur('prix_jour'):
                raise serializers.ValidationError({'actif': ["Indiquez le prix par jour du propriétaire avant d'activer le véhicule."]})
            if not valeur('proprietaire'):
                raise serializers.ValidationError({'actif': ["Indiquez le propriétaire avant d'activer le véhicule."]})
            if not (valeur('sans_chauffeur', True) or valeur('avec_chauffeur', True)):
                raise serializers.ValidationError({'actif': ['Proposez au moins une formule (avec ou sans chauffeur).']})
        return data


class CategoriesView(ListeAdmin):
    nom_objet = "categorie_vehicule"
    serializer_class = CategorieSerializer
    queryset = CategorieVehiculeModel.objects.prefetch_related('photos').order_by('ordre', 'nom')


class CategorieView(FicheAdmin):
    nom_objet = "categorie_vehicule"
    serializer_class = CategorieSerializer
    queryset = CategorieVehiculeModel.objects.prefetch_related('photos')


class AjoutPhotoSerializer(serializers.Serializer):
    image = ChampPhoto()


def _photos(request, categorie):
    return PhotoVehiculeSerializer(categorie.photos.all(), many=True, context={'request': request}).data


def _journal_photos(request, categorie, **details):
    journaliser("backoffice_modification", request, utilisateur=request.user, objet="categorie_vehicule",
                id=str(categorie.pk), libelle=str(categorie), champs=['photos'], **details)


class PhotosCategorieView(APIView):
    """POST {image} (multipart): adds a photo at the end (MAX_PAR_CATEGORIE at most). Returns all the photos."""
    permission_classes = [EstAdministrateur]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        categorie = get_object_or_404(CategorieVehiculeModel, pk=pk)
        if categorie.photos.count() >= PhotoVehiculeModel.MAX_PAR_CATEGORIE:
            return Response({'detail': f"{PhotoVehiculeModel.MAX_PAR_CATEGORIE} photos au maximum par catégorie."},
                            status=status.HTTP_400_BAD_REQUEST)
        donnees = AjoutPhotoSerializer(data=request.data)
        donnees.is_valid(raise_exception=True)
        dernier = categorie.photos.aggregate(m=Max('ordre'))['m']
        photo = PhotoVehiculeModel.objects.create(categorie=categorie, image=donnees.validated_data['image'],
                                                  ordre=0 if dernier is None else dernier + 1)
        _journal_photos(request, categorie, photo_ajoutee=photo.pk)
        return Response(_photos(request, categorie), status=status.HTTP_201_CREATED)


class PhotoCategorieView(APIView):
    """PATCH {principale: true}: the photo moves to the first position. DELETE: removes it. Returns all the photos."""
    permission_classes = [EstAdministrateur]

    def _photo(self, pk, photo_id):
        return get_object_or_404(PhotoVehiculeModel.objects.select_related('categorie'), pk=photo_id, categorie_id=pk)

    def patch(self, request, pk, photo_id):
        photo = self._photo(pk, photo_id)
        if request.data.get('principale') is True:
            with transaction.atomic():
                autres = [p for p in photo.categorie.photos.select_for_update() if p.pk != photo.pk]
                for i, p in enumerate([photo, *autres]):
                    if p.ordre != i:
                        p.ordre = i
                        p.save(update_fields=['ordre'])
            _journal_photos(request, photo.categorie, photo_principale=photo.pk)
        return Response(_photos(request, photo.categorie))

    def delete(self, request, pk, photo_id):
        photo = self._photo(pk, photo_id)
        categorie, fichier = photo.categorie, photo.image
        photo.delete()
        fichier.delete(save=False)
        _journal_photos(request, categorie, photo_retiree=photo_id)
        return Response(_photos(request, categorie))


class LieuSerializer(serializers.ModelSerializer):
    class Meta:
        model = LieuRemiseModel
        fields = ['id', 'nom', 'ville', 'fuseau', 'adresse_requise', 'frais', 'actif', 'ordre']


class LieuxView(ListeAdmin):
    nom_objet = "lieu_remise"
    serializer_class = LieuSerializer
    queryset = LieuRemiseModel.objects.order_by('ordre', 'nom')


class LieuView(FicheAdmin):
    nom_objet = "lieu_remise"
    serializer_class = LieuSerializer
    queryset = LieuRemiseModel.objects.all()


class PartenaireSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(many=True, queryset=CategorieVehiculeModel.objects.all(), required=False)
    lieux = serializers.PrimaryKeyRelatedField(many=True, queryset=LieuRemiseModel.objects.all())
    nb_locations = serializers.IntegerField(source='locations.count', read_only=True)
    nb_vehicules = serializers.IntegerField(source='vehicules.count', read_only=True)
    commission_pourcent = serializers.SerializerMethodField()

    class Meta:
        model = PartenaireLocationModel
        fields = ['id', 'nom', 'contact', 'telephone', 'email', 'categories', 'lieux', 'actif', 'fondateur_debut',
                  'fondateur_fin', 'pays_versement', 'operateur_versement', 'numero_versement', 'nb_locations',
                  'nb_vehicules', 'commission_pourcent']

    def get_commission_pourcent(self, obj):
        params = ParametresLocationModel.courants()
        return float(services.taux_commission(params, obj)) if params else None

    def validate(self, data):
        debut = data.get('fondateur_debut', getattr(self.instance, 'fondateur_debut', None))
        fin = data.get('fondateur_fin', getattr(self.instance, 'fondateur_fin', None))
        if bool(debut) != bool(fin) or (debut and fin <= debut):
            raise serializers.ValidationError({'fondateur_fin': ['Indiquez le début et la fin du Programme Fondateurs (fin après le début).']})
        pays = data.get('pays_versement', getattr(self.instance, 'pays_versement', ''))
        operateur = data.get('operateur_versement', getattr(self.instance, 'operateur_versement', ''))
        if operateur not in operateurs_du_pays(pays):
            raise serializers.ValidationError({'operateur_versement': ["Cet opérateur n'existe pas dans ce pays."]})
        return data


class PartenairesView(ListeAdmin):
    nom_objet = "loueur"
    serializer_class = PartenaireSerializer
    queryset = PartenaireLocationModel.objects.prefetch_related('categories', 'lieux').order_by('nom')


class PartenaireView(FicheAdmin):
    nom_objet = "loueur"
    serializer_class = PartenaireSerializer
    queryset = PartenaireLocationModel.objects.all()


# --- Rental follow-up -------------------------------------------------------------------------

def _chauffeur(chauffeur_id) -> dict | None:
    c = transferts.fiche_chauffeur(chauffeur_id) if chauffeur_id else None
    return {'id': chauffeur_id, 'nom': f"{c['prenom']} {c['nom']}" if c else ''} if chauffeur_id else None


def _location(loc: LocationModel) -> dict:
    return {
        'id': str(loc.id), 'reference': loc.reference, 'statut': loc.statut, 'statut_libelle': loc.get_statut_display(),
        'voyageur': {'nom': _nom(loc.voyageur), 'email': loc.voyageur.email}, 'telephone': loc.telephone,
        'categorie': loc.libelle, 'formule': loc.formule, 'formule_libelle': loc.get_formule_display(),
        'proprietaire_vehicule': loc.categorie.proprietaire_id if loc.categorie_id else None,
        'jours_hors_lome': loc.jours_hors_lome, 'jours_hors_pays': loc.jours_hors_pays,
        'prix_vehicule': loc.prix_jour * loc.jours, 'prix_chauffeur': loc.prix_chauffeur, 'primes': loc.primes,
        'commission': loc.commission, 'part_kwaba_chauffeur': loc.part_kwaba_chauffeur,
        'chauffeur_demande': _chauffeur(loc.chauffeur_demande_id),
        'chauffeur_partenaire': _chauffeur(loc.chauffeur_partenaire_id),
        'lieu_prise': loc.lieu_prise.nom, 'adresse_prise': loc.adresse_prise,
        'lieu_retour': loc.lieu_retour.nom, 'adresse_retour': loc.adresse_retour,
        'debut': loc.debut, 'fin': loc.fin, 'jours': loc.jours, 'passagers': loc.passagers,
        'prix': loc.prix, 'caution': loc.caution, 'precisions': loc.precisions,
        'caution_en_ligne': bool(loc.caution_gardee), 'caution_retenue': loc.caution_retenue,
        'caution_motif': loc.caution_motif, 'caution_restituee_le': loc.caution_restituee_le,
        'conducteur': loc.conducteur, 'permis_numero': loc.permis_numero, 'permis_pays': loc.permis_pays,
        'partenaire': {'id': loc.partenaire_id, 'nom': loc.partenaire.nom} if loc.partenaire_id else None,
        'vehicule': loc.vehicule, 'immatriculation': loc.immatriculation,
        'chauffeur_nom': loc.chauffeur_nom, 'chauffeur_telephone': loc.chauffeur_telephone,
        'cree_le': loc.cree_le,
    }


def _locations():
    return LocationModel.objects.select_related('voyageur', 'categorie', 'lieu_prise', 'lieu_retour', 'partenaire')


class LocationsView(APIView):
    """Rentals, next pick-ups first. Filters: status, q (reference, email, phone, driver)."""
    permission_classes = [EstAdministrateur]

    def get(self, request):
        qs = _locations().order_by('debut')
        if (statut := request.query_params.get('statut')) in dict(LocationModel.STATUTS):
            qs = qs.filter(statut=statut)
        if q := request.query_params.get('q', '').strip():
            filtre = Q(voyageur__email__icontains=q) | Q(telephone__icontains=q) | Q(conducteur__icontains=q)
            if len(q.split('-')[-1]) >= 4:
                filtre |= Q(id__istartswith=q.split('-')[-1])
            qs = qs.filter(filtre)
        return _paginer(request, qs, _location)


class LocationPartenairesView(APIView):
    """Owners who can provide this vehicle at this handover place, and partner drivers (the driver asked for
    again and the Excellence ones first)."""
    permission_classes = [EstAdministrateur]

    def get(self, request, pk):
        loc = _locations().filter(pk=pk).first()
        if not loc:
            return Response({'detail': 'Location introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        partenaires = [{'id': p.id, 'nom': p.nom, 'telephone': p.telephone} for p in services.partenaires_disponibles(loc)]
        if request.query_params.get('chauffeurs'):
            return Response({
                'partenaires': partenaires,
                'chauffeurs': [{'id': c['id'], 'nom': f"{c['prenom']} {c['nom']}", 'telephone': c['telephone'],
                                'excellence': c['excellence'], 'demande': c['id'] == loc.chauffeur_demande_id}
                               for c in services.chauffeurs_disponibles(loc)]
                if loc.avec_chauffeur else [],
            })
        return Response(partenaires)


class AttributionSerializer(serializers.Serializer):
    partenaire = serializers.PrimaryKeyRelatedField(queryset=PartenaireLocationModel.objects.filter(actif=True),
                                                    required=False, allow_null=True, default=None)
    chauffeur = serializers.IntegerField(required=False, allow_null=True, default=None)
    vehicule = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    immatriculation = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')

    def validate_chauffeur(self, valeur):
        if valeur is None:
            return None
        chauffeur = transferts.fiche_chauffeur(valeur)
        if not chauffeur or not chauffeur['actif']:
            raise serializers.ValidationError('Chauffeur introuvable.')
        return chauffeur


class LocationAttribuerView(APIView):
    """Assigns the owner (and the handed-over vehicle) and/or the partner driver: the traveller receives their
    contact details, they receive the rental details."""
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        loc = _locations().filter(pk=pk).first()
        if not loc:
            return Response({'detail': 'Location introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        donnees = AttributionSerializer(data=request.data)
        donnees.is_valid(raise_exception=True)
        d = donnees.validated_data
        try:
            services.attribuer(loc, **d)
        except services.LocationErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        journaliser("backoffice_modification", request, utilisateur=request.user, objet="location", id=str(loc.pk),
                    libelle=loc.reference, partenaire=getattr(d['partenaire'], 'nom', ''),
                    chauffeur=f"{d['chauffeur']['prenom']} {d['chauffeur']['nom']}" if d['chauffeur'] else '')
        return Response(_location(_locations().get(pk=pk)))


class RetenueSerializer(serializers.Serializer):
    montant = serializers.IntegerField(min_value=0)
    motif = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')


class LocationCautionView(APIView):
    """Amount withheld from the deposit (damage reported by the owner), before it is returned to the traveller; 0 cancels it."""
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        loc = _locations().filter(pk=pk).first()
        if not loc:
            return Response({'detail': 'Location introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        donnees = RetenueSerializer(data=request.data)
        donnees.is_valid(raise_exception=True)
        try:
            services.retenir_caution(loc, **donnees.validated_data)
        except services.LocationErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        journaliser("backoffice_modification", request, utilisateur=request.user, objet="location", id=str(loc.pk),
                    libelle=loc.reference, operation="retenue_caution", **donnees.validated_data)
        return Response(_location(_locations().get(pk=pk)))


class LocationAnnulerView(APIView):
    """Cancellation by Kwa-Ba: full refund of the traveller (no owner available, for example)."""
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        motif, erreur = _motif(request.data.get('motif'))
        if erreur:
            return erreur
        loc = _locations().filter(pk=pk).first()
        if not loc:
            return Response({'detail': 'Location introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            rembourse = services.annuler(loc, par='plateforme')
        except services.LocationErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        journaliser("backoffice_modification", request, utilisateur=request.user, objet="location", id=str(loc.pk),
                    libelle=loc.reference, operation="annulation", rembourse=rembourse, motif=motif)
        return Response(_location(_locations().get(pk=pk)))
