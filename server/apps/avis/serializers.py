from rest_framework import serializers

from apps.reservations import api as reservations

from .models import AvisModel, CRITERES


class AvisSerializer(serializers.ModelSerializer):
    auteur = serializers.SerializerMethodField()
    sejour = serializers.SerializerMethodField()
    criteres = serializers.SerializerMethodField()

    class Meta:
        model = AvisModel
        fields = ['id', 'note', 'criteres', 'commentaire', 'auteur', 'sejour', 'reponse_hote', 'reponse_le', 'created_at']

    def get_auteur(self, obj):
        # First name + initial of the last name: credible identity without exposing the full name
        u = obj.auteur
        return {
            'prenom': u.first_name,
            'initiale': (u.last_name[:1] + '.') if u.last_name else '',
            'avatar_url': u.avatar.url if u.avatar else None,
        }

    def get_sejour(self, obj):
        if '_sejours' not in self.context:
            instance = self.parent.instance if self.parent is not None else self.instance
            avis = instance if isinstance(instance, AvisModel) else list(instance)
            ids = [avis.reservation_id] if isinstance(avis, AvisModel) else [a.reservation_id for a in avis]
            self.context['_sejours'] = reservations.resumes(ids)
        sejour = self.context['_sejours'].get(obj.reservation_id)
        return serializers.DateField().to_representation(sejour['check_in']) if sejour else None

    def get_criteres(self, obj):
        return {cle: getattr(obj, cle) for cle in CRITERES}


class AvisCreateSerializer(serializers.ModelSerializer):
    # Without the automatic uniqueness validator: the "already reviewed" case is handled by motif_refus with a clear message
    reservation = serializers.UUIDField(source='reservation_id')
    commentaire = serializers.CharField(min_length=20, max_length=2000, error_messages={
        'min_length': 'Décrivez votre séjour en au moins 20 caractères.',
    })

    class Meta:
        model = AvisModel
        fields = ['reservation', 'note', *CRITERES.keys(), 'commentaire']

    def validate_reservation(self, valeur):
        if valeur not in reservations.resumes([valeur]):
            raise serializers.ValidationError('Réservation introuvable.')
        return valeur

    def validate_commentaire(self, value):
        return value.strip()


class ReponseHoteSerializer(serializers.Serializer):
    reponse = serializers.CharField(min_length=2, max_length=1000)
