import unicodedata
import uuid
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Count, Min, Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle

from .alertes import signaler_liberation
from .archivage import ArchivageImpossible, archiver
from . import stock
from .disponibilites import a_des_reservations, periodes_indisponibles, verrouiller, verrouiller_types
from .models import BlocageModel, HebergementModel, HebergementPhotoModel, TypeLogementModel
from .occupations import reservations
from apps.securite import fraude
from apps.securite.photos import InvalidPhoto, normalize_photo

from . import types_logement
from .serializers import (
    BlocageSerializer, HebergementSerializer, HebergementCreateSerializer, RechercheSerializer, TypeLogementSerializer,
)
from apps.contrats import api as contrats
from apps.favoris import api as favoris
from apps.verifications import api as verifications

HOST_ROLES = ('hote', 'admin')
MAX_FENETRE_JOURS = 548  # 18 months of calendar per request
MAX_RESULTATS = 200
# Search with dates: listings whose availability is computed before sorting (available ones first)
MAX_CANDIDATS = 600
# Unit types of one establishment (a hotel's room types)
MAX_TYPES = 30


def _context(request, proprietaire=False):
    """Adds the signed-in user's favourite ids to compute is_favorite.

    `proprietaire`: the host also sees the reason of a verification refusal.
    """
    contexte = {'request': request, 'proprietaire': proprietaire}
    if request.user and request.user.is_authenticated:
        contexte['favorite_ids'] = favoris.ids_favoris(request.user.id)
    return contexte



def _remettre_en_verification(hebergement, avant: dict) -> bool:
    """After a change by the host: a refused listing goes back into verification, and a verified listing too
    if what the agent checked (address, city, photos) changed. Returns True if it is put back."""
    if hebergement.statut_verification == 'en_attente':
        return False
    change = any(avant[champ] != getattr(hebergement, champ) for champ in hebergement.CHAMPS_VERIFIES)
    if hebergement.statut_verification == 'verifiee' and not change:
        return False
    deja_verifiee = hebergement.statut_verification == 'verifiee'
    hebergement.statut_verification, hebergement.motif_refus = 'en_attente', ''
    hebergement.save(update_fields=['statut_verification', 'motif_refus', 'updated_at'])
    verifications.visite_a_planifier(hebergement.id, modification=deja_verifiee)
    return True


def _signaler_coordonnees(request, serializer, objet_id) -> None:
    """Contact details refused in a listing: attempt reported to the back-office (Anti-fraud)."""
    trouvailles = getattr(serializer, 'trouvailles', None)
    if trouvailles:
        fraude.signaler(request.user.id, 'annonce', objet_id, trouvailles)

class HebergementListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        recherche = RechercheSerializer.depuis(request.query_params)
        if not recherche.is_valid():
            return Response(recherche.errors, status=status.HTTP_400_BAD_REQUEST)
        filtres = recherche.validated_data

        qs = HebergementModel.objects.publiees().select_related('host', 'host__piece_identite')

        city = request.query_params.get('city')
        if city:
            qs = qs.filter(Q(city__icontains=city) | Q(location__icontains=city))

        type_ = request.query_params.get('type')
        if type_:
            qs = qs.filter(type=type_)

        if 'price_min' in filtres:
            qs = qs.filter(price_per_night__gte=filtres['price_min'])
        if 'price_max' in filtres:
            qs = qs.filter(price_per_night__lte=filtres['price_max'])

        guests = request.query_params.get('guests')
        if guests and guests.isdigit():
            qs = qs.filter(max_guests__gte=int(guests))
        if request.query_params.get('petit_dejeuner') == 'inclus':
            qs = qs.filter(petit_dejeuner='inclus')
        # Requested amenities (?equipements=piscine,wifi): the listing must have all of them
        equipements = [e.strip() for e in request.query_params.get('equipements', '').split(',') if e.strip()]
        for equipement in equipements[:10]:
            qs = qs.filter(amenities__contains=[equipement])

        search = request.query_params.get('q')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(city__icontains=search) | Q(location__icontains=search))

        sort = request.query_params.get('sort')
        if sort == 'prix_asc':
            qs = qs.order_by('price_per_night')
        elif sort == 'prix_desc':
            qs = qs.order_by('-price_per_night')
        elif sort == 'note':
            qs = qs.order_by('-rating')
        else:
            # Hosts who signed up first come first: promise made to the hosts registered before the opening
            qs = qs.order_by('created_at')

        # At most MAX_RESULTATS listings per request: the list is not paginated, a request must not be able to
        # load (and serialise) the whole database
        limit = request.query_params.get('limit')
        limite = min(int(limit), MAX_RESULTATS) if limit and limit.isdigit() else MAX_RESULTATS

        # With dates, a full listing stays in the results (badge "full on these dates", next available date), after
        # the available ones; ?disponibles=1 keeps only the available ones
        check_in, check_out = filtres.get('check_in'), filtres.get('check_out')
        disponibilites = {}
        if check_in and check_out:
            candidats = list(qs[:MAX_CANDIDATS])
            disponibilites = stock.disponibilites_etablissements([h.id for h in candidats], check_in, check_out)
            libre = lambda h: disponibilites.get(h.id, {}).get('disponible', False)  # noqa: E731
            if filtres.get('disponibles'):
                candidats = [h for h in candidats if libre(h)]
            candidats.sort(key=lambda h: not libre(h))  # stable: the chosen sort is kept within each group
            resultats = candidats[:limite]
        else:
            resultats = qs[:limite]

        donnees = HebergementSerializer(resultats, many=True, context=_context(request)).data
        for ligne in donnees:
            ligne['disponibilite'] = disponibilites.get(uuid.UUID(ligne['id'])) if disponibilites else None
        return Response({'results': donnees, 'count': len(donnees)})

    def post(self, request):
        if request.user.role not in HOST_ROLES:
            return Response(
                {'detail': 'Seuls les hôtes peuvent publier un hébergement.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if contrats.preinscription_requise(request.user):
            return Response(
                {'detail': "Acceptez d'abord la pré-inscription pour créer votre annonce.", 'code': 'preinscription_requise'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            verifications.verifier_limite_annonces(request.user)
        except verifications.VerificationErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = HebergementCreateSerializer(data=request.data)
        if not serializer.is_valid():
            _signaler_coordonnees(request, serializer, 'nouvelle')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        hebergement = serializer.save(host=request.user)  # its default unit type: signals.type_par_defaut
        # Visible to travellers only after an agent's visit (offered once the host's identity is verified)
        verifications.visite_a_planifier(hebergement.id)
        return Response(
            HebergementSerializer(hebergement, context=_context(request, proprietaire=True)).data,
            status=status.HTTP_201_CREATED,
        )


class MyHebergementsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = HebergementModel.objects.filter(host=request.user).select_related('host', 'host__piece_identite')
        serializer = HebergementSerializer(qs, many=True, context=_context(request, proprietaire=True))
        return Response({'results': serializer.data, 'count': len(serializer.data)})


class CityListView(APIView):
    """Popular destinations: cities with their number of available listings."""
    permission_classes = [AllowAny]

    def get(self, request):
        rows = (
            HebergementModel.objects.publiees()
            .values('city')
            .annotate(count=Count('id'), min_price=Min('price_per_night'))
            .order_by('-count', 'city')[:8]
        )
        results = []
        for row in rows:
            cover = (
                HebergementModel.objects.publiees().filter(city=row['city'])
                .exclude(image_url='')
                .order_by('-rating')
                .values_list('image_url', flat=True)
                .first()
            )
            results.append({**row, 'image_url': cover or ''})
        return Response({'results': results})


def _sans_accents(texte):
    """"Lomé" → "lome": travellers often type without accents."""
    decompose = unicodedata.normalize('NFKD', texte.casefold())
    return ''.join(c for c in decompose if not unicodedata.combining(c)).strip()


class SuggestionsView(APIView):
    """Autocompletion of the search bar: cities then listings whose name matches.

    Published cities are few: they are compared in Python, ignoring accents and case
    ("lome" finds "Lomé"), those starting with the input first.
    """
    permission_classes = [AllowAny]
    MAX_VILLES = 5
    MAX_LOGEMENTS = 4

    def get(self, request):
        saisie = request.query_params.get('q', '')[:100]
        cle = _sans_accents(saisie)
        if not cle:
            return Response({'villes': [], 'logements': []})

        publiees = HebergementModel.objects.publiees()
        villes = []
        for ligne in publiees.values('city').annotate(count=Count('id')):
            nom = _sans_accents(ligne['city'])
            if cle in nom:
                villes.append((not nom.startswith(cle), -ligne['count'], ligne['city'], ligne['count']))
        villes.sort()

        logements = (
            publiees.filter(name__icontains=saisie.strip())
            .order_by('-rating', 'name')
            .values('id', 'name', 'city', 'image_url')[:self.MAX_LOGEMENTS]
        )
        return Response({
            'villes': [{'city': ville, 'count': nombre} for _, _, ville, nombre in villes[:self.MAX_VILLES]],
            'logements': list(logements),
        })


class HebergementDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def _get_object(self, pk):
        try:
            return HebergementModel.objects.select_related('host', 'host__piece_identite').get(pk=pk)
        except HebergementModel.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get_object(pk)
        proprietaire = request.user.is_authenticated and obj is not None and obj.host_id == request.user.id
        verificateur = request.user.is_authenticated and request.user.role in verifications.ROLES_VERIFICATEURS
        # Listing not verified yet (or hidden): visible only to its host and the agents
        if not obj or not (obj.est_publiee or proprietaire or verificateur):
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        # The page shows the unit types (a hotel's rooms) to choose from
        contexte = {**_context(request, proprietaire=proprietaire), 'avec_types': True}
        return Response(HebergementSerializer(obj, context=contexte).data)

    def patch(self, request, pk):
        obj = self._get_object(pk)
        if not obj:
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if obj.host_id != request.user.id:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = HebergementCreateSerializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            _signaler_coordonnees(request, serializer, obj.pk)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        avant = {champ: getattr(obj, champ) for champ in HebergementModel.CHAMPS_VERIFIES}
        serializer.save()
        _remettre_en_verification(obj, avant)
        return Response(HebergementSerializer(obj, context=_context(request, proprietaire=True)).data)

    def delete(self, request, pk):
        obj = self._get_object(pk)
        if not obj:
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if obj.host_id != request.user.id:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            archiver(obj)
        except ArchivageImpossible as e:
            return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PhotoUploadView(APIView):
    """POST multipart ("file" field): saves a normalised photo and returns its public URL."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'hebergement_photo_upload'

    def post(self, request):
        if request.user.role not in HOST_ROLES:
            return Response({'detail': 'Seuls les hôtes peuvent envoyer des photos.'}, status=status.HTTP_403_FORBIDDEN)

        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'file': ['Aucun fichier reçu.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            content, width, height = normalize_photo(uploaded)
        except InvalidPhoto as e:
            return Response({'file': [str(e)]}, status=status.HTTP_400_BAD_REQUEST)

        photo = HebergementPhotoModel(owner=request.user, width=width, height=height)
        photo.image.save('photo.jpg', content, save=False)
        photo.save()
        return Response(_photo_json(request, photo), status=status.HTTP_201_CREATED)


class PhotoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        photo = HebergementPhotoModel.objects.filter(pk=pk, owner=request.user).first()
        if not photo:
            return Response({'detail': 'Photo introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        photo.image.delete(save=False)
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _photo_json(request, photo):
    return {
        'id': str(photo.id),
        'url': request.build_absolute_uri(photo.image.url),
        'width': photo.width,
        'height': photo.height,
    }


def _uuid(valeur):
    try:
        return uuid.UUID(str(valeur))
    except ValueError:
        return None


def _parse_date(value, defaut):
    if not value:
        return defaut
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class DisponibiliteView(APIView):
    """GET ?debut=&fin=: unavailable periods. The listing's host receives the details (bookings, blocks)."""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        hebergement = HebergementModel.objects.filter(pk=pk).only('id', 'host_id').first()
        utilisateur = request.user
        est_hote = utilisateur.is_authenticated and utilisateur.id == getattr(hebergement, 'host_id', None)
        # A listing not published yet (in verification, hidden) shows its calendar only to its host and to the team
        equipe = utilisateur.is_authenticated and utilisateur.role in ('agent', 'admin')
        if not hebergement or not (est_hote or equipe or HebergementModel.objects.publiees().filter(pk=pk).exists()):
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.localdate()
        debut = _parse_date(request.query_params.get('debut'), today)
        fin = _parse_date(request.query_params.get('fin'), today + timedelta(days=365))
        if not debut or not fin or fin <= debut:
            return Response({'detail': 'Période invalide (format AAAA-MM-JJ).'}, status=status.HTTP_400_BAD_REQUEST)
        if (fin - debut).days > MAX_FENETRE_JOURS:
            return Response({'detail': f'Période limitée à {MAX_FENETRE_JOURS} jours.'}, status=status.HTTP_400_BAD_REQUEST)

        # ?type_logement=: the full nights of that unit type (otherwise: nights when no type has a unit left)
        type_logement = None
        if request.query_params.get('type_logement'):
            type_logement = TypeLogementModel.objects.filter(
                pk=_uuid(request.query_params['type_logement']), hebergement_id=hebergement.id, actif=True).first()
            if type_logement is None:
                return Response({'detail': 'Type de logement inconnu.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'debut': debut,
            'fin': fin,
            'periodes': periodes_indisponibles(hebergement.id, debut, fin, detail=est_hote, type_logement=type_logement),
        })


class BlocageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        hebergement = HebergementModel.objects.filter(pk=pk).first()
        if not hebergement:
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if hebergement.host_id != request.user.id:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = BlocageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        debut, fin = serializer.validated_data['debut'], serializer.validated_data['fin']
        # Without a unit type, the whole establishment is closed; with one, only that type
        type_logement = serializer.validated_data.get('type_logement')
        if type_logement is not None and type_logement.hebergement_id != hebergement.id:
            return Response({'type_logement': ["Ce type n'appartient pas à cet établissement."]}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Unit types first, then the establishment: the same order as a booking (its type, then the insert that
            # reads the establishment), so the two never deadlock. A simultaneous booking cannot take these nights.
            verrouiller_types(hebergement.types.values_list('pk', flat=True))
            verrouiller(hebergement.id)
            # Nights already booked are not closed: the host must first handle the booking
            if a_des_reservations(hebergement.id, debut, fin, type_logement=type_logement):
                return Response(
                    {'detail': 'Cette période contient une réservation. Contactez le voyageur avant de fermer ces dates.'},
                    status=status.HTTP_409_CONFLICT,
                )
            deja = BlocageModel.objects.filter(hebergement=hebergement, debut__lt=fin, fin__gt=debut)
            if type_logement is not None:
                deja = deja.filter(Q(type_logement=type_logement) | Q(type_logement__isnull=True))
            if deja.exists():
                return Response({'detail': 'Une partie de ces dates est déjà fermée.'}, status=status.HTTP_409_CONFLICT)
            blocage = serializer.save(hebergement=hebergement)
        return Response(BlocageSerializer(blocage).data, status=status.HTTP_201_CREATED)


class BlocageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        blocage = BlocageModel.objects.filter(pk=pk, hebergement__host=request.user).first()
        if not blocage:
            return Response({'detail': 'Blocage introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        blocage.delete()
        signaler_liberation(blocage.hebergement_id, blocage.debut, blocage.fin)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _type_du_proprietaire(request, pk):
    return TypeLogementModel.objects.select_related('hebergement').filter(pk=pk, hebergement__host=request.user).first()


class TypesLogementView(APIView):
    """GET: the unit types of one of my establishments (inactive ones included). POST: add one."""
    permission_classes = [IsAuthenticated]

    def _etablissement(self, request, pk):
        return HebergementModel.objects.filter(pk=pk, host=request.user).first()

    def get(self, request, pk):
        hebergement = self._etablissement(request, pk)
        if not hebergement:
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        types = hebergement.types.all()
        return Response({'results': TypeLogementSerializer(types, many=True).data})

    def post(self, request, pk):
        hebergement = self._etablissement(request, pk)
        if not hebergement:
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TypeLogementSerializer(data=request.data)
        if not serializer.is_valid():
            _signaler_coordonnees(request, serializer, hebergement.pk)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if hebergement.types.count() >= MAX_TYPES:
            return Response({'detail': f'{MAX_TYPES} types de logement au plus par établissement.'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            type_logement = serializer.save(hebergement=hebergement)
            types_logement.recalculer_etablissement(hebergement)
            signaler_liberation(hebergement.id)
        return Response(TypeLogementSerializer(type_logement).data, status=status.HTTP_201_CREATED)


class TypeLogementDetailView(APIView):
    """PATCH: change a unit type (a lower quantity never overbooks a future night). DELETE: remove it, if it was
    never booked (otherwise deactivate it). An establishment always keeps an active type."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        type_logement = _type_du_proprietaire(request, pk)
        if not type_logement:
            return Response({'detail': 'Type de logement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TypeLogementSerializer(type_logement, data=request.data, partial=True)
        if not serializer.is_valid():
            _signaler_coordonnees(request, serializer, type_logement.hebergement_id)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        hebergement = type_logement.hebergement
        with transaction.atomic():
            # Same lock as a booking of this type: the units counted below cannot change meanwhile
            verrouiller_types([type_logement.pk])
            quantite = serializer.validated_data.get('quantite', type_logement.quantite)
            reservees = types_logement.unites_reservees_max(type_logement)
            if quantite < reservees:
                return Response({'quantite': [
                    f"{reservees} logements de ce type sont déjà réservés certaines nuits : la quantité ne peut pas être inférieure."]},
                    status=status.HTTP_409_CONFLICT)
            if serializer.validated_data.get('actif') is False and not hebergement.types.filter(actif=True).exclude(pk=pk).exists():
                return Response({'actif': ["L'établissement doit garder au moins un type de logement proposé."]},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            types_logement.recalculer_etablissement(hebergement)
            # More units, or a type offered again
            signaler_liberation(hebergement.id)
        return Response(TypeLogementSerializer(type_logement).data)

    def delete(self, request, pk):
        type_logement = _type_du_proprietaire(request, pk)
        if not type_logement:
            return Response({'detail': 'Type de logement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        hebergement = type_logement.hebergement
        if not hebergement.types.filter(actif=True).exclude(pk=pk).exists():
            return Response({'detail': "L'établissement doit garder au moins un type de logement proposé."},
                            status=status.HTTP_400_BAD_REQUEST)
        if reservations().type_reserve(type_logement.pk):
            return Response({'detail': "Ce type a déjà des réservations : désactivez-le plutôt."}, status=status.HTTP_409_CONFLICT)
        with transaction.atomic():
            type_logement.delete()
        types_logement.recalculer_etablissement(hebergement)
        return Response(status=status.HTTP_204_NO_CONTENT)
