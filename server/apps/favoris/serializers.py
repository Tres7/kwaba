from rest_framework import serializers

from apps.hebergements import api as hebergements


def favoris_json(favoris, request) -> list[dict]:
    cartes = hebergements.cartes([f.hebergement_id for f in favoris], request)
    return [{
        'id': str(f.id), 'hebergement': f.hebergement_id, 'hebergement_detail': cartes[f.hebergement_id],
        'created_at': serializers.DateTimeField().to_representation(f.created_at),
    } for f in favoris if f.hebergement_id in cartes]


class FavoriCreateSerializer(serializers.Serializer):
    hebergement = serializers.UUIDField()

    def validate_hebergement(self, valeur):
        if not hebergements.est_publiee(valeur):
            raise serializers.ValidationError('Hébergement introuvable.')
        return valeur
