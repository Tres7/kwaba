from rest_framework import serializers

from apps.reservations.models import ReservationModel
from .models import AvisModel, CRITERES


class AvisSerializer(serializers.ModelSerializer):
    auteur = serializers.SerializerMethodField()
    sejour = serializers.DateField(source='reservation.check_in', read_only=True)
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

    def get_criteres(self, obj):
        return {cle: getattr(obj, cle) for cle in CRITERES}


class AvisCreateSerializer(serializers.ModelSerializer):
    # Without the automatic uniqueness validator: the "already reviewed" case is handled by motif_refus with a clear message
    reservation = serializers.PrimaryKeyRelatedField(queryset=ReservationModel.objects.all())
    commentaire = serializers.CharField(min_length=20, max_length=2000, error_messages={
        'min_length': 'Décrivez votre séjour en au moins 20 caractères.',
    })

    class Meta:
        model = AvisModel
        fields = ['reservation', 'note', *CRITERES.keys(), 'commentaire']

    def validate_commentaire(self, value):
        return value.strip()


class ReponseHoteSerializer(serializers.Serializer):
    reponse = serializers.CharField(min_length=2, max_length=1000)
