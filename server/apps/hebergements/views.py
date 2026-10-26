import unicodedata
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Count, Min, ProtectedError, Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle

from .disponibilites import a_des_reservations, filtre_actives, periodes_indisponibles, verrouiller
from .models import BlocageModel, HebergementModel, HebergementPhotoModel
from .photos import InvalidPhoto, normalize_photo
from apps.securite import fraude

from .serializers import BlocageSerializer, HebergementSerializer, HebergementCreateSerializer, RechercheSerializer
from apps.contrats import preinscription
from apps.verifications import services as verifications

HOST_ROLES = ('hote', 'admin')
MAX_FENETRE_JOURS = 548  # 18 months of calendar per request
MAX_RESULTATS = 200


def _context(request, proprietaire=False):
    """Adds the signed-in user's favourite ids to compute is_favorite.

    `proprietaire`: the host also sees the reason of a verification refusal.
    """
    contexte = {'request': request, 'proprietaire': proprietaire}
    if request.user and request.user.is_authenticated:
        from apps.favoris.models import FavoriModel
        contexte['favorite_ids'] = set(FavoriModel.objects.filter(user=request.user).values_list('hebergement_id', flat=True))
    return contexte



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

        # Excludes the listings already booked over the requested period
        check_in, check_out = filtres.get('check_in'), filtres.get('check_out')
        if check_in and check_out:
            busy = HebergementModel.objects.filter(
                filtre_actives('reservations__'),
                reservations__check_in__lt=check_out,
                reservations__check_out__gt=check_in,
            ).values('id')
            fermes = BlocageModel.objects.filter(debut__lt=check_out, fin__gt=check_in).values('hebergement_id')
            qs = qs.exclude(id__in=busy).exclude(id__in=fermes)

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
        qs = qs[:limite]

        serializer = HebergementSerializer(qs, many=True, context=_context(request))
        return Response({'results': serializer.data, 'count': len(serializer.data)})

    def post(self, request):
        if request.user.role not in HOST_ROLES:
            return Response(
                {'detail': 'Seuls les hôtes peuvent publier un hébergement.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if preinscription.requise(request.user):
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

        hebergement = serializer.save(host=request.user)
        # Visible to travellers only after an agent's visit (offered once the host's identity is verified)
        verifications.visite_a_planifier(hebergement)
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
        return Response(HebergementSerializer(obj, context=_context(request, proprietaire=proprietaire)).data)

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
        verifications.remettre_en_verification(obj, avant)
        return Response(HebergementSerializer(obj, context=_context(request, proprietaire=True)).data)

    def delete(self, request, pk):
        obj = self._get_object(pk)
        if not obj:
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if obj.host_id != request.user.id:
            return Response({'detail': 'Non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            obj.delete()
        except ProtectedError:
            return Response(
                {'detail': "Cette annonce a des réservations payées : elle ne peut pas être supprimée. Masquez-la plutôt."},
                status=status.HTTP_409_CONFLICT,
            )
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
        if not hebergement:
            return Response({'detail': 'Hébergement introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.localdate()
        debut = _parse_date(request.query_params.get('debut'), today)
        fin = _parse_date(request.query_params.get('fin'), today + timedelta(days=365))
        if not debut or not fin or fin <= debut:
            return Response({'detail': 'Période invalide (format AAAA-MM-JJ).'}, status=status.HTTP_400_BAD_REQUEST)
        if (fin - debut).days > MAX_FENETRE_JOURS:
            return Response({'detail': f'Période limitée à {MAX_FENETRE_JOURS} jours.'}, status=status.HTTP_400_BAD_REQUEST)

        est_hote = request.user.is_authenticated and request.user.id == hebergement.host_id
        return Response({
            'debut': debut,
            'fin': fin,
            'periodes': periodes_indisponibles(hebergement.id, debut, fin, detail=est_hote),
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

        with transaction.atomic():
            # Listing lock: a simultaneous booking cannot take these nights during the closure
            verrouiller(hebergement.id)
            # Nights already booked are not closed: the host must first handle the booking
            if a_des_reservations(hebergement.id, debut, fin):
                return Response(
                    {'detail': 'Cette période contient une réservation. Contactez le voyageur avant de fermer ces dates.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if BlocageModel.objects.filter(hebergement=hebergement, debut__lt=fin, fin__gt=debut).exists():
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
        return Response(status=status.HTTP_204_NO_CONTENT)
