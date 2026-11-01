"""Back-office: experiences of the Discover page (creation, change, photo, publication, deletion)."""
from rest_framework import generics, serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from apps.securite.audit import journaliser
from apps.securite.backoffice import ChampPhoto, Journalise, ListeAdmin
from apps.securite.permissions import EstAdministrateur

from .models import ExperienceModel


class ExperienceSerializer(serializers.ModelSerializer):
    # Uploaded photo (checked, re-encoded as JPEG); "photo" gives the displayed address, uploaded or external
    image = ChampPhoto(required=False, allow_null=True, write_only=True)
    photo = serializers.SerializerMethodField()

    class Meta:
        model = ExperienceModel
        fields = ['id', 'categorie', 'nom', 'nom_en', 'etiquette', 'etiquette_en', 'ville', 'pays', 'pays_en', 'description',
                  'description_en', 'prix', 'gratuit', 'image', 'photo', 'credit_photo', 'credit_photo_url', 'actif', 'ordre']

    def get_photo(self, obj):
        return obj.photo(self.context.get('request'))

    def validate(self, data):
        if data.get('gratuit', getattr(self.instance, 'gratuit', False)):
            data['prix'] = None  # free: no price
        return data


class ExperiencesAdminView(ListeAdmin):
    nom_objet = "experience"
    serializer_class = ExperienceSerializer
    queryset = ExperienceModel.objects.all()


class ExperienceAdminView(Journalise, generics.RetrieveUpdateDestroyAPIView):
    """Read, update and deletion (editorial content, no history to preserve)."""
    nom_objet = "experience"
    permission_classes = [EstAdministrateur]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    serializer_class = ExperienceSerializer
    queryset = ExperienceModel.objects.all()

    def perform_destroy(self, instance):
        journaliser("backoffice_suppression", self.request, utilisateur=self.request.user, objet=self.nom_objet,
                    id=str(instance.pk), libelle=str(instance))
        fichier = instance.image
        instance.delete()
        if fichier:
            fichier.delete(save=False)
