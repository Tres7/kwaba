from django.utils import timezone
from rest_framework import serializers
from .models import ReservationModel
from apps.avis import api as avis
from apps.hebergements import types_logement
from apps.hebergements.disponibilites import conflit, verrouiller_types
from apps.hebergements.serializers import HebergementSerializer
from apps.paiements import services as paiements, tarifs


class ReservationSerializer(serializers.ModelSerializer):
    hebergement_detail = HebergementSerializer(source='hebergement', read_only=True)
    nights = serializers.IntegerField(read_only=True)
    reference = serializers.CharField(read_only=True)
    guest_name = serializers.SerializerMethodField()
    avis_id = serializers.SerializerMethodField()
    peut_evaluer = serializers.SerializerMethodField()
    montants = serializers.SerializerMethodField()
    paiement = serializers.SerializerMethodField()
    remboursement = serializers.SerializerMethodField()

    type_logement_nom = serializers.CharField(source='type_logement.nom', read_only=True, default=None)

    class Meta:
        model = ReservationModel
        fields = [
            'id', 'hebergement', 'hebergement_detail', 'type_logement', 'type_logement_nom', 'nb_unites',
            'check_in', 'check_out',
            'guests_count', 'total_price', 'status', 'payment_method',
            'message', 'nights', 'reference', 'guest_name', 'avis_id', 'peut_evaluer', 'created_at',
            'montants', 'paiement', 'remboursement', 'expire_le', 'annule_par',
        ]
        read_only_fields = ['id', 'status', 'created_at']

    def get_montants(self, obj):
        m = tarifs.montants_de(obj)
        return {
            'prix_nuits': m.prix_nuits, 'frais_service': m.frais_service, 'taux_frais': m.taux_frais, 'total': m.total,
            'commission_hote': m.commission_hote, 'montant_hote': m.montant_hote,
        }

    def get_paiement(self, obj):
        """Status of the last payment: null if none (online payment inactive at booking time)."""
        dernier = max(obj.paiements.all(), key=lambda p: p.cree_le, default=None)
        return dernier.statut if dernier else None

    def get_remboursement(self, obj):
        lignes = list(obj.remboursements.all())
        if not lignes:
            return None
        if any(r.statut == 'attente_numero' for r in lignes):
            statut = 'attente_numero'
        elif all(r.statut == 'envoye' for r in lignes):
            statut = 'envoye'
        else:
            statut = 'en_cours'
        return {'montant': sum(r.montant for r in lignes), 'statut': statut}

    def _avis(self) -> dict:
        """Reviews of the serialized bookings, read once for the whole list."""
        if '_avis' not in self.context:
            instance = self.parent.instance if self.parent is not None else self.instance
            reservations = [instance] if isinstance(instance, ReservationModel) else list(instance)
            self.context['_avis'] = avis.avis_des_reservations(r.pk for r in reservations)
        return self.context['_avis']

    def get_avis_id(self, obj):
        avis_id = self._avis().get(obj.pk)
        return str(avis_id) if avis_id else None

    def get_peut_evaluer(self, obj):
        request = self.context.get('request')
        if not (request and request.user.is_authenticated):
            return False
        sejour = {'voyageur_id': obj.guest_id, 'statut': obj.status, 'check_out': obj.check_out}
        return avis.motif_refus(sejour, request.user.id, obj.pk in self._avis()) is None

    def get_guest_name(self, obj):
        return f"{obj.guest.first_name} {obj.guest.last_name}".strip()


# Units of one type in a single booking (a group); beyond that, several bookings
MAX_UNITES = 20


class ReservationCreateSerializer(serializers.ModelSerializer):
    # Total shown to the traveller in the summary: if it no longer matches the server's calculation (price changed
    # by the host in the meantime, different rate), the booking is refused so that they see the new total before paying
    total_attendu = serializers.IntegerField(required=False, write_only=True, min_value=0)

    # Units booked of the unit type (a hotel room type); the establishment's default type when none is chosen
    nb_unites = serializers.IntegerField(required=False, min_value=1, max_value=MAX_UNITES)

    class Meta:
        model = ReservationModel
        fields = [
            'hebergement', 'type_logement', 'nb_unites', 'check_in', 'check_out',
            'guests_count', 'payment_method', 'message', 'total_attendu',
        ]

    def validate(self, data):
        hebergement = data['hebergement']
        check_in, check_out = data['check_in'], data['check_out']
        request = self.context.get('request')

        if check_in < timezone.localdate():
            raise serializers.ValidationError({'check_in': "La date d'arrivée ne peut pas être dans le passé."})
        if check_in >= check_out:
            raise serializers.ValidationError({'check_out': "La date de départ doit être après la date d'arrivée."})
        if (check_out - check_in).days > 90:
            raise serializers.ValidationError({'check_out': "La durée maximale d'un séjour est de 90 nuits."})
        type_logement = data.get('type_logement') or types_logement.type_par_defaut(hebergement)
        if type_logement.hebergement_id != hebergement.id or not type_logement.actif:
            raise serializers.ValidationError(
                {'type_logement': "Ce type de logement n'est pas proposé par cet établissement."})
        nb_unites = data.get('nb_unites', 1)
        if nb_unites > type_logement.quantite:
            raise serializers.ValidationError(
                {'nb_unites': f"Cet établissement propose {type_logement.quantite} logement(s) de ce type au plus."})
        data['type_logement'], data['nb_unites'] = type_logement, nb_unites
        if data.get('guests_count', 1) < 1:
            raise serializers.ValidationError({'guests_count': "Au moins 1 voyageur."})
        capacite = type_logement.capacite * nb_unites
        if data.get('guests_count', 1) > capacite:
            raise serializers.ValidationError({'guests_count': f"Ce logement accueille au maximum {capacite} voyageurs."})
        if not hebergement.est_publiee:
            raise serializers.ValidationError({'hebergement': "Cet hébergement n'est plus disponible."})
        if request and hebergement.host_id == request.user.id:
            raise serializers.ValidationError({'hebergement': "Vous ne pouvez pas réserver votre propre hébergement."})

        # Same rule as the displayed calendar: units left night by night, dates closed by the host.
        # The unit-type lock (held by the view's transaction until create) prevents two simultaneous bookings from
        # taking the last units; the other types of the establishment stay bookable meanwhile.
        verrouiller_types([type_logement.id])
        motif = conflit(hebergement.id, check_in, check_out, type_logement=type_logement, nb=nb_unites)
        if motif:
            raise serializers.ValidationError({'check_in': motif})

        total_attendu = data.pop('total_attendu', None)
        if total_attendu is not None:
            voyageur = request.user if request else None
            total = tarifs.devis(hebergement, (check_out - check_in).days, voyageur=voyageur,
                                 type_logement=type_logement, nb_unites=nb_unites).total
            if total != total_attendu:
                raise serializers.ValidationError({'total_attendu': [
                    f"Le prix a changé : le total est maintenant de {total:,} FCFA. Vérifiez le récapitulatif avant de payer."
                    .replace(',', ' ')]})
        return data

    def create(self, validated_data):
        hebergement = validated_data['hebergement']
        nights = (validated_data['check_out'] - validated_data['check_in']).days
        montants = tarifs.devis(hebergement, nights, voyageur=validated_data.get('guest'),
                                type_logement=validated_data['type_logement'], nb_unites=validated_data['nb_unites'])
        if paiements.paiement_actif():
            # Dates held while paying; confirmed by the FedaPay webhook
            etat = {'status': 'pending', 'expire_le': timezone.now() + paiements.delai_paiement()}
        else:
            etat = {'status': 'confirmed'}
        return ReservationModel.objects.create(
            total_price=montants.total,
            prix_nuits=montants.prix_nuits,
            frais_service=montants.frais_service,
            commission_hote=montants.commission_hote,
            **etat,
            **validated_data,
        )
