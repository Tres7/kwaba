"""Shared back-office building blocks: admin access, audit log at every write, normalised photos."""
from rest_framework import generics, serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import journaliser
from .permissions import EstAdministrateur
from .photos import InvalidPhoto, normalize_photo


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


PAGE_SIZE = 20
PAGE_SIZE_MAX = 100


def _entier(valeur, defaut: int, minimum: int = 1, maximum: int | None = None) -> int:
    try:
        nombre = int(valeur)
    except (TypeError, ValueError):
        return defaut
    nombre = max(nombre, minimum)
    return min(nombre, maximum) if maximum else nombre


def paginer(request, qs, serialiser, en_lot=False) -> Response:
    """Page of a back-office list (?page=, ?page_size=). `en_lot`: the serialiser receives the whole page."""
    page = _entier(request.query_params.get('page'), 1)
    taille = _entier(request.query_params.get('page_size'), PAGE_SIZE, maximum=PAGE_SIZE_MAX)
    debut = (page - 1) * taille
    objets = list(qs[debut:debut + taille])
    return Response({
        'results': serialiser(objets) if en_lot else [serialiser(objet) for objet in objets],
        'count': qs.count(),
        'page': page,
        'page_size': taille,
    })


MOTIF_MIN, MOTIF_MAX = 5, 500


class VueAdmin(APIView):
    permission_classes = [EstAdministrateur]


def booleen(valeur):
    """'true' / 'false' (URL parameter) → bool; any other value → None (filter ignored)."""
    return {'true': True, 'false': False}.get((valeur or '').lower())


def motif(valeur):
    """Required reason for deletions and cancellations: (reason, error response or None)."""
    texte = (valeur or '').strip()
    if not MOTIF_MIN <= len(texte) <= MOTIF_MAX:
        return texte, Response(
            {'motif': [f'Indiquez un motif de {MOTIF_MIN} à {MOTIF_MAX} caractères.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return texte, None


def nom(utilisateur) -> str:
    return f'{utilisateur.first_name} {utilisateur.last_name}'.strip() or utilisateur.email


def introuvable(quoi: str) -> Response:
    return Response({'detail': f'{quoi} introuvable.'}, status=status.HTTP_404_NOT_FOUND)


def entier(valeur, defaut: int, minimum: int = 1, maximum: int | None = None) -> int:
    return _entier(valeur, defaut, minimum, maximum)
