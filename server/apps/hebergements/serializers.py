from rest_framework import serializers
import re
from datetime import timedelta

from django.utils import timezone

from apps.paiements import api as paiements
from apps.securite import coordonnees
from apps.securite.images import MESSAGE as IMAGE_REFUSEE, url_image_autorisee
from apps.users import api as users

from . import positions
from .models import BlocageModel, HebergementModel, TypeLogementModel

# Amenities a host can tick, by category (labels and icons: client/src/components/hebergement/AmenityBadge.tsx).
# Stored in the `amenities` JSON list: adding one needs no migration.
AMENITIES = [
    # Essentials
    'wifi', 'clim', 'ventilateur', 'eau_chaude', 'moustiquaire', 'tv', 'fer_repasser', 'lave_linge', 'espace_travail',
    # Power and water
    'groupe_electrogene', 'solaire', 'reserve_eau',
    # Kitchen
    'cuisine', 'refrigerateur', 'barbecue',
    # Outdoors and leisure
    'piscine', 'jardin', 'terrasse', 'acces_plage', 'gym', 'spa',
    # Safety
    'gardien', 'videosurveillance', 'parking', 'coffre_fort', 'extincteur',
    # Services
    'menage', 'linge', 'cuisinier', 'lit_bebe', 'plain_pied',
]
# House rules, stored in the same list: one value of each pair at most, none when the host did not say
REGLES = [
    ('fumeur_autorise', 'non_fumeur'),
    ('animaux_acceptes', 'animaux_interdits'),
    ('fetes_autorisees', 'fetes_interdites'),
]
AMENITIES += [valeur for paire in REGLES for valeur in paire]
# Room of a photo: numbered for the bedrooms and bathrooms ("chambre_2"), otherwise one of these
PIECES = ('piece_principale', 'salon', 'cuisine', 'salle_a_manger', 'toilettes', 'terrasse', 'balcon', 'jardin', 'piscine',
          'salle_de_sport', 'exterieur', 'entree', 'vue', 'parking', 'autre',
          # Spaces of a hotel, an aparthotel or a guesthouse
          'reception', 'chambres', 'salles_de_bain', 'restaurant', 'bar', 'salle_de_reunion')
MAX_TYPES_CHAMBRES = 30
# Photos of a listing: enough for every room of a big house (bedrooms, pool, garden, gym…). Field agents' report of
# 2026-11-09: 10 were not enough. The photos of a hotel's room type stay at 10 each.
MAX_PHOTOS_ANNONCE = 20
# Longest stay a search takes into account: the longest one that can be booked
MAX_NUITS_RECHERCHE = 90
PIECE_NUMEROTEE = re.compile(r'^(chambre|salle_de_bain)_([1-9]|[1-4][0-9]|50)$')
LEGENDE_MANQUANTE = "Indiquez la pièce de chaque photo (chambre 1, salon…)."
# What the host states before sending a listing; `attestation`: the information is true and they may rent this place out
DECLARATIONS = ('cameras', 'animaux', 'travaux', 'attestation')


class HebergementSerializer(serializers.ModelSerializer):
    host_id = serializers.UUIDField(read_only=True)
    host_name = serializers.SerializerMethodField()
    hote_verifie = serializers.SerializerMethodField()
    hote_fondateur = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    motif_refus = serializers.SerializerMethodField()
    en_ligne = serializers.SerializerMethodField()
    statut_annonce = serializers.SerializerMethodField()
    frais_voyageur = serializers.SerializerMethodField()
    types = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()

    class Meta:
        model = HebergementModel
        fields = [
            'id', 'name', 'description', 'type', 'espace', 'city', 'location', 'latitude', 'longitude', 'position',
            'price_per_night', 'rating', 'review_count', 'image_url', 'images', 'legendes_photos',
            'max_guests', 'amenities', 'is_available', 'host_id', 'host_name', 'hote_verifie', 'hote_fondateur',
            'is_favorite', 'created_at', 'statut_verification', 'verifiee_le', 'motif_refus', 'en_ligne', 'statut_annonce',
            'chambres', 'salles_de_bain', 'lits_doubles', 'lits_simples', 'canapes_lits', 'point_repere',
            'petit_dejeuner', 'petit_dejeuner_prix', 'arrivee_a_partir', 'depart_avant',
            'politique_annulation', 'frais_voyageur', 'types',
        ]
        read_only_fields = ['id', 'rating', 'review_count', 'host_id', 'created_at', 'statut_verification', 'verifiee_le']

    def to_representation(self, instance):
        donnees = super().to_representation(instance)
        donnees['legendes_photos'] = donnees.get('legendes_photos') or {}
        # Listings published before the filtering: contact details hidden from travellers (the host sees their text)
        if not self.context.get('proprietaire'):
            for champ in ('name', 'description', 'location'):
                if donnees.get(champ):
                    donnees[champ] = coordonnees.analyser(donnees[champ])[0]
            # Anti-bypass: the exact position and the landmark would lead to the host without booking
            del donnees['latitude'], donnees['longitude'], donnees['point_repere']
        return donnees

    def _par_hote(self, cle: str, obj, charger):
        """Read once for the listings being serialised (a list: the whole page)."""
        cache = self.context.setdefault(cle, {})
        if obj.host_id not in cache:
            parent = self.parent
            annonces = list(parent.instance) if isinstance(parent, serializers.ListSerializer) and parent.instance is not None else []
            ids = {h.host_id for h in annonces} | {obj.host_id}
            cache.update(charger(ids - cache.keys()))
        return cache.get(obj.host_id)

    def get_host_name(self, obj):
        hote = self._par_hote('_hotes', obj, lambda ids: {i: None for i in ids} | users.comptes(ids))
        return hote.get_full_name() if hote else ''

    def get_hote_verifie(self, obj):
        # "Verified host" badge: identity document checked by Kwa-Ba
        from apps.verifications.api import hotes_verifies  # local import: verifications reads the listings

        def charger(ids):
            verifies = hotes_verifies(ids)
            return {i: i in verifies for i in ids}
        return self._par_hote('_hotes_verifies', obj, charger)

    def get_hote_fondateur(self, obj):
        # "Founder host" badge: one of the first 50 individual hosts (Founders Programme)
        def charger(ids):
            fondateurs = paiements.hotes_fondateurs(ids)
            return {i: i in fondateurs for i in ids}
        return self._par_hote('_hotes_fondateurs', obj, charger)

    def get_position(self, obj):
        return positions.approchee(obj)

    def get_motif_refus(self, obj):
        # The agent's message for the host: never shown to travellers
        return obj.motif_refus if self.context.get('proprietaire') else ''

    def get_en_ligne(self, obj):
        # For the host only: is the listing actually public (verified, not hidden, opening done, agreement signed)?
        return obj.est_publiee if self.context.get('proprietaire') else None

    def get_statut_annonce(self, obj):
        return obj.statut_annonce if self.context.get('proprietaire') else None

    def get_frais_voyageur(self, obj):
        """Service fee rate for the visitor: 6 %, or 3 % if they already stayed with this host (loyal customer)."""
        request = self.context.get('request')
        if '_hotes_visites' not in self.context:
            self.context['_hotes_visites'] = paiements.hotes_deja_visites(request.user if request else None)
        reduit = obj.host_id in self.context['_hotes_visites']
        return float(paiements.frais_reduits() if reduit else paiements.frais_voyageur())

    def get_types(self, obj):
        """Unit types to choose from (listing page only: one query, never per row of a list)."""
        if not self.context.get('avec_types'):
            return None
        return [{
            'id': str(t.id), 'nom': t.nom, 'description': t.description, 'capacite': t.capacite,
            'prix_nuit': float(t.prix_nuit), 'quantite': t.quantite, 'photos': t.photos,
        } for t in obj.types.filter(actif=True)]

    def get_is_favorite(self, obj):
        favorite_ids = self.context.get('favorite_ids')
        if favorite_ids is None:
            return False
        return obj.id in favorite_ids


class HebergementCreateSerializer(serializers.ModelSerializer):
    # A hotel's room types, created with the listing ("Double standard", 80 rooms…): written only, then managed in
    # the host space (TypeLogementModel)
    types_chambres = serializers.ListField(child=serializers.DictField(), required=False, write_only=True,
                                           max_length=MAX_TYPES_CHAMBRES)

    class Meta:
        model = HebergementModel
        fields = [
            'name', 'description', 'type', 'city', 'location', 'point_repere', 'latitude', 'longitude',
            'price_per_night', 'image_url', 'images', 'legendes_photos', 'max_guests', 'types_chambres',
            'amenities', 'is_available',
            'chambres', 'salles_de_bain', 'lits_doubles', 'lits_simples', 'canapes_lits',
            'petit_dejeuner', 'petit_dejeuner_prix', 'arrivee_a_partir', 'depart_avant', 'politique_annulation',
            'declarations',
        ]
        extra_kwargs = {
            'latitude': {'min_value': -85, 'max_value': 85},
            'longitude': {'min_value': -180, 'max_value': 180},
            'max_guests': {'max_value': 20},
            'chambres': {'max_value': 200},
            'salles_de_bain': {'min_value': 1, 'max_value': 200},
            'lits_doubles': {'max_value': 200},
            'lits_simples': {'max_value': 200},
            'canapes_lits': {'max_value': 200},
            'petit_dejeuner_prix': {'min_value': 0, 'max_value': 1000000},
        }

    # Required at creation; a listing published before they were added can be changed without them
    POSITION_MANQUANTE = "Placez votre logement sur la carte."
    DETAILS_OBLIGATOIRES = {
        'latitude': POSITION_MANQUANTE,
        'point_repere': "Indiquez un point de repère pour trouver le logement.",
        'chambres': "Indiquez le nombre de chambres (0 pour un studio).",
        'salles_de_bain': "Indiquez le nombre de salles de bain.",
        'petit_dejeuner': "Indiquez si le petit-déjeuner est inclus, en option ou non proposé.",
    }

    def validate(self, data):
        etablissement = data.get('type', getattr(self.instance, 'type', None)) in HebergementModel.ETABLISSEMENTS
        types = data.get('types_chambres') or []
        if not self.partial:
            # A hotel describes its rooms by type: no bedrooms, bathrooms or beds of a house
            obligatoires = {k: m for k, m in self.DETAILS_OBLIGATOIRES.items()
                            if not etablissement or k not in ('chambres', 'salles_de_bain')}
            manquants = {k: [m] for k, m in obligatoires.items() if data.get(k) in (None, '')}
            if not etablissement and not any(data.get(k) for k in ('lits_doubles', 'lits_simples', 'canapes_lits')):
                manquants['lits'] = ["Indiquez au moins un lit."]
            if any(not (u.get('nom') and u.get('prix_nuit') and u.get('quantite') and u.get('capacite')) for u in types):
                manquants['types_chambres'] = ["Indiquez le nom, le prix, le nombre de chambres et la capacité de chaque type."]
            if manquants:
                raise serializers.ValidationError(manquants)
        if not etablissement:
            # Left from a type chosen then changed: a house has no room types to create
            data.pop('types_chambres', None)
            types = []
        complets = [u for u in types if u.get('prix_nuit') and u.get('capacite')]
        if complets:
            # The listing shows the cheapest room ("from") and the largest one
            data['price_per_night'] = min(u['prix_nuit'] for u in complets)
            data['max_guests'] = max(u['capacite'] for u in complets)
        latitude = data.get('latitude', getattr(self.instance, 'latitude', None))
        longitude = data.get('longitude', getattr(self.instance, 'longitude', None))
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError({'latitude': [self.POSITION_MANQUANTE]})
        formule = data.get('petit_dejeuner', getattr(self.instance, 'petit_dejeuner', ''))
        if formule == 'option' and not data.get('petit_dejeuner_prix', getattr(self.instance, 'petit_dejeuner_prix', None)):
            raise serializers.ValidationError({'petit_dejeuner_prix': ["Indiquez le prix du petit-déjeuner par personne."]})
        if formule != 'option' and 'petit_dejeuner' in data:
            data['petit_dejeuner_prix'] = None
        self._legendes(data)
        return data

    def _legendes(self, data):
        """Keeps the room of the listing's photos only, and of all of them for a new listing."""
        if not ({'images', 'image_url', 'legendes_photos'} & data.keys()) and self.partial:
            return
        photos = set(data.get('images', getattr(self.instance, 'images', None)) or [])
        photos |= {data.get('image_url', getattr(self.instance, 'image_url', ''))} - {''}
        legendes = data.get('legendes_photos', getattr(self.instance, 'legendes_photos', None)) or {}
        data['legendes_photos'] = {url: piece for url, piece in legendes.items() if url in photos}
        if not self.partial and photos - data['legendes_photos'].keys():
            raise serializers.ValidationError({'legendes_photos': [LEGENDE_MANQUANTE]})

    COORDONNEES_REFUSEES = ("Les coordonnées (téléphone, email, site, réseaux sociaux) ne sont pas autorisées dans l'annonce : "
                            "les voyageurs vous écrivent par la messagerie Kwa-Ba.")

    def _sans_coordonnees(self, value):
        """Anti-bypass: no way to reach the host outside the site. The elements found are kept
        for the back-office alert (reported by the view)."""
        _, trouvailles = coordonnees.analyser(value or '')
        if coordonnees.masquees(trouvailles):
            self.trouvailles = getattr(self, 'trouvailles', []) + trouvailles
            raise serializers.ValidationError(self.COORDONNEES_REFUSEES)
        return value

    def validate_name(self, value):
        return self._sans_coordonnees(value)

    def validate_description(self, value):
        return self._sans_coordonnees(value)

    def validate_location(self, value):
        return self._sans_coordonnees(value)

    def validate_point_repere(self, value):
        return self._sans_coordonnees(value.strip())

    def validate_price_per_night(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le prix doit être supérieur à 0.")
        return value

    def validate_max_guests(self, value):
        # At 0, no booking is possible anymore (at least 1 traveller per booking)
        if value < 1:
            raise serializers.ValidationError("Le logement doit accueillir au moins 1 voyageur.")
        return value

    def validate_amenities(self, value):
        unknown = [a for a in value if a not in AMENITIES]
        if unknown:
            raise serializers.ValidationError(f"Équipements inconnus : {', '.join(unknown)}")
        if any(oui in value and non in value for oui, non in REGLES):
            raise serializers.ValidationError("Une règle de la maison ne peut pas être à la fois autorisée et interdite.")
        return value

    def validate_image_url(self, value):
        if value and not url_image_autorisee(value):
            raise serializers.ValidationError(IMAGE_REFUSEE)
        return value

    def validate_images(self, value):
        if not isinstance(value, list) or not all(isinstance(u, str) for u in value):
            raise serializers.ValidationError("Liste d'URL attendue.")
        if not all(url_image_autorisee(u) for u in value):
            raise serializers.ValidationError(IMAGE_REFUSEE)
        if len(value) > MAX_PHOTOS_ANNONCE:
            raise serializers.ValidationError(f"{MAX_PHOTOS_ANNONCE} photos au plus par annonce.")
        return value

    def validate_types_chambres(self, value):
        """Each type: name, price per night, number of identical rooms, guests per room. A draft may hold unfinished
        lines: only a wrong value is refused there, the missing ones at creation (validate)."""
        propres = []
        for u in value:
            try:
                propre = {
                    'nom': str(u.get('nom') or '').strip()[:120],
                    'prix_nuit': int(u.get('prix_nuit') or 0),
                    'quantite': int(u.get('quantite') or 0),
                    'capacite': int(u.get('capacite') or 0),
                }
            except (TypeError, ValueError):
                raise serializers.ValidationError("Types de chambres invalides.")
            if propre['prix_nuit'] < 0 or propre['prix_nuit'] > 10_000_000:
                raise serializers.ValidationError("Prix par nuit invalide.")
            if propre['quantite'] > 500 or propre['capacite'] > 50 or propre['quantite'] < 0 or propre['capacite'] < 0:
                raise serializers.ValidationError("500 chambres et 50 personnes par chambre au plus.")
            if propre['nom']:
                self._sans_coordonnees(propre['nom'])
            propres.append(propre)
        return propres

    def create(self, validated_data):
        types = validated_data.pop('types_chambres', None) or []
        hebergement = super().create(validated_data)
        if types:
            from . import types_logement

            # The default type (created with the listing) becomes the first one, the others follow
            premier, *autres = types
            defaut = hebergement.types.first()
            for champ, valeur in premier.items():
                setattr(defaut, champ, valeur)
            defaut.ordre = 0
            defaut.save()
            TypeLogementModel.objects.bulk_create([TypeLogementModel(hebergement=hebergement, ordre=i, **u)
                                                   for i, u in enumerate(autres, start=1)])
            types_logement.recalculer_etablissement(hebergement)
        return hebergement

    def update(self, instance, validated_data):
        validated_data.pop('types_chambres', None)  # managed in the host space once the listing exists
        return super().update(instance, validated_data)

    def validate_legendes_photos(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict) or len(value) > 20 or not all(
                isinstance(url, str) and isinstance(piece, str) and (piece in PIECES or PIECE_NUMEROTEE.match(piece))
                for url, piece in value.items()):
            raise serializers.ValidationError("Pièces des photos invalides.")
        return value

    def validate_declarations(self, value):
        if value is None:
            return value
        if not isinstance(value, dict) or set(value) - set(DECLARATIONS) or not all(isinstance(v, bool) for v in value.values()):
            raise serializers.ValidationError("Déclarations invalides.")
        return value


class TypeLogementSerializer(serializers.ModelSerializer):
    """A unit type managed by its host: a hotel room type and how many identical units it has."""
    COORDONNEES_REFUSEES = HebergementCreateSerializer.COORDONNEES_REFUSEES
    _sans_coordonnees = HebergementCreateSerializer._sans_coordonnees

    class Meta:
        model = TypeLogementModel
        fields = ['id', 'nom', 'description', 'capacite', 'prix_nuit', 'quantite', 'photos', 'actif', 'ordre']
        read_only_fields = ['id']

    def validate_nom(self, value):
        return self._sans_coordonnees(value)

    def validate_description(self, value):
        return self._sans_coordonnees(value)

    def validate_capacite(self, value):
        if not 1 <= value <= 50:
            raise serializers.ValidationError("De 1 à 50 voyageurs par logement.")
        return value

    def validate_prix_nuit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le prix doit être supérieur à 0.")
        return value

    def validate_quantite(self, value):
        if not 1 <= value <= 500:
            raise serializers.ValidationError("De 1 à 500 logements identiques.")
        return value

    def validate_photos(self, value):
        if not isinstance(value, list) or not all(isinstance(u, str) for u in value):
            raise serializers.ValidationError("Liste d'URL attendue.")
        if not all(url_image_autorisee(u) for u in value):
            raise serializers.ValidationError(IMAGE_REFUSEE)
        return value[:10]


class BlocageSerializer(serializers.ModelSerializer):
    type_logement_nom = serializers.CharField(source='type_logement.nom', read_only=True, default=None)

    class Meta:
        model = BlocageModel
        fields = ['id', 'debut', 'fin', 'motif', 'type_logement', 'type_logement_nom', 'quantite', 'created_at']
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {'quantite': {'min_value': 1}}

    def validate(self, data):
        today = timezone.localdate()
        if data['fin'] <= data['debut']:
            raise serializers.ValidationError({'fin': 'La fin doit être après le début.'})
        if data.get('quantite'):
            type_logement = data.get('type_logement')
            if type_logement is None:
                raise serializers.ValidationError({'quantite': ["Choisissez le type de chambre dont fermer une partie."]})
            if data['quantite'] > type_logement.quantite:
                raise serializers.ValidationError({'quantite': [f"Ce type compte {type_logement.quantite} unité(s)."]})
        if data['debut'] < today:
            raise serializers.ValidationError({'debut': 'Impossible de bloquer des dates passées.'})
        if data['fin'] > today + timedelta(days=730):
            raise serializers.ValidationError({'fin': 'Le calendrier est limité à deux ans.'})
        return data


class RechercheSerializer(serializers.Serializer):
    """Search parameters whose invalid value would make the SQL query fail (500 instead of 400).

    An empty parameter is ignored, like a missing one.
    """
    price_min = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    price_max = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False)
    check_in = serializers.DateField(required=False)
    check_out = serializers.DateField(required=False)
    disponibles = serializers.BooleanField(required=False)

    def validate(self, data):
        # Dates are used only as a pair, for a stay that can be booked: departure after arrival, arrival not in the
        # past, 90 nights at most. Availability is computed night by night: an unbounded stay would hold a worker.
        debut, fin = data.get('check_in'), data.get('check_out')
        if not (debut and fin and debut < fin and debut >= timezone.localdate() and (fin - debut).days <= MAX_NUITS_RECHERCHE):
            data.pop('check_in', None)
            data.pop('check_out', None)
        return data

    @classmethod
    def depuis(cls, query_params):
        return cls(data={nom: valeur for nom, valeur in query_params.items() if nom in cls._declared_fields and valeur})
