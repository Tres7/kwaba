"""Shared back-office building blocks: admin access, audit log at every write, normalised photos."""
from rest_framework import generics, serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from apps.hebergements.photos import InvalidPhoto, normalize_photo
from apps.securite.audit import journaliser
from apps.securite.permissions import EstAdministrateur


class ChampPhoto(serializers.ImageField):
    """Photo uploaded from the back-office: checked then re-encoded as JPEG without metadata (like listings)."""

    def to_internal_value(self, data):
        if not hasattr(data, "size"):
            raise serializers.ValidationError("Envoyez une image (fichier).")
        try:
            contenu, _, _ = normalize_photo(data)
        except InvalidPhoto as exc:
            raise serializers.ValidationError(str(exc))
        contenu.name = "photo.jpg"
        return contenu

    def to_representation(self, value):
        if not value:
            return None
        requete = self.context.get("request")
        return requete.build_absolute_uri(value.url) if requete else value.url


class Journalise:
    """Every creation or change is written to the audit log (object, id, changed fields)."""
    nom_objet = ""

    def perform_create(self, serializer):
        objet = serializer.save()
        journaliser("backoffice_creation", self.request, utilisateur=self.request.user,
                    objet=self.nom_objet, id=str(objet.pk), libelle=str(objet))

    def perform_update(self, serializer):
        objet = serializer.save()
        journaliser("backoffice_modification", self.request, utilisateur=self.request.user,
                    objet=self.nom_objet, id=str(objet.pk), libelle=str(objet),
                    champs=sorted(k for k in self.request.data.keys() if k in serializer.fields))


class ListeAdmin(Journalise, generics.ListCreateAPIView):
    """Full list (short reference lists: categories, places, rental companies…) and creation."""
    permission_classes = [EstAdministrateur]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    pagination_class = None


class FicheAdmin(Journalise, generics.RetrieveUpdateAPIView):
    """Read and update of an item (no deletion: it is deactivated, so the history stays consistent)."""
    permission_classes = [EstAdministrateur]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
