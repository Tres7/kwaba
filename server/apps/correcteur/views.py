from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import services


class VerifierView(APIView):
    """POST {texte, langue} → {disponible, fautes}. Only an aid: nothing is ever refused because of a mistake."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'correcteur'

    def post(self, request):
        texte = request.data.get('texte')
        if not isinstance(texte, str):
            return Response({'texte': ['Texte attendu.']}, status=status.HTTP_400_BAD_REQUEST)
        if len(texte) > services.LONGUEUR_MAX:
            return Response({'texte': [f'{services.LONGUEUR_MAX} caractères maximum.']},
                            status=status.HTTP_400_BAD_REQUEST)
        langue = request.data.get('langue')
        fautes = services.verifier(texte, langue if isinstance(langue, str) else 'fr') if texte.strip() else []
        return Response({'disponible': fautes is not None, 'fautes': fautes or []})
