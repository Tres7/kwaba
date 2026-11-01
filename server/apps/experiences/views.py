from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ExperienceModel

# The offered experiences are in Togo (audit no. 3): entries of other countries (Marrakech, Dakar…) stay in the
# back-office but are no longer shown on the site
PAYS_PROPOSE = 'Togo'
# Kept in the back-office for later, not shown on the site for now
CATEGORIES_MASQUEES = ('restaurants',)


def experience_json(request, e: ExperienceModel) -> dict:
    return {
        'id': e.id, 'categorie': e.categorie, 'nom': e.nom, 'nom_en': e.nom_en, 'etiquette': e.etiquette,
        'etiquette_en': e.etiquette_en, 'ville': e.ville, 'pays': e.pays, 'pays_en': e.pays_en,
        'description': e.description, 'description_en': e.description_en, 'prix': e.prix, 'gratuit': e.gratuit,
        'image': e.photo(request), 'credit_photo': e.credit_photo, 'credit_photo_url': e.credit_photo_url,
    }


class ExperiencesView(APIView):
    """GET: active experiences of the Discover page (texts in French and English, the client chooses)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        experiences = ExperienceModel.objects.filter(actif=True, pays__iexact=PAYS_PROPOSE).exclude(categorie__in=CATEGORIES_MASQUEES)
        return Response([experience_json(request, e) for e in experiences])
