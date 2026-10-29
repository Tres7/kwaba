import json

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.hebergements import api as hebergements
from apps.securite.audit import journaliser
from apps.terrain import api as terrain

from . import services
from .fichiers import FichierInvalide, piece_identite
from .models import PieceIdentiteModel, VisiteModel

ROLES_HOTE = ('hote', 'admin')


class EstVerificateur(IsAuthenticated):
    """Field agents and administrators: role read from the database at every request."""
    message = "Réservé aux agents de vérification."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role in services.ROLES_VERIFICATEURS


def _piece_json(piece: PieceIdentiteModel | None) -> dict:
    if not piece:
        return {'statut': 'absente'}
    return {
        'statut': piece.statut, 'type_piece': piece.type_piece, 'type_libelle': piece.get_type_piece_display(),
        'soumise_le': piece.soumise_le, 'verifiee_le': piece.verifiee_le, 'motif_refus': piece.motif_refus,
    }


class MaPieceIdentiteView(APIView):
    """GET: status of my identity document. POST (multipart type_piece, fichier): send or replace it."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_scope = 'verification_piece'

    def get_throttles(self):
        return [ScopedRateThrottle()] if self.request.method == 'POST' else []

    def get(self, request):
        return Response(_piece_json(PieceIdentiteModel.objects.filter(hote=request.user).first()))

    def post(self, request):
        if request.user.role not in ROLES_HOTE:
            return Response({'detail': 'Réservé aux hôtes.'}, status=status.HTTP_403_FORBIDDEN)
        type_piece = request.data.get('type_piece')
        if type_piece not in dict(PieceIdentiteModel.TYPES):
            return Response({'type_piece': ["Choisissez le type de pièce."]}, status=status.HTTP_400_BAD_REQUEST)
        fichier = request.FILES.get('fichier')
        if not fichier:
            return Response({'fichier': ['Aucun fichier reçu.']}, status=status.HTTP_400_BAD_REQUEST)

        piece = PieceIdentiteModel.objects.filter(hote=request.user).first()
        if piece and piece.statut == 'verifiee':
            return Response({'detail': 'Votre identité est déjà vérifiée.'}, status=status.HTTP_409_CONFLICT)
        try:
            contenu, extension, type_contenu = piece_identite(fichier)
        except FichierInvalide as exc:
            return Response({'fichier': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        piece = piece or PieceIdentiteModel(hote=request.user)
        if piece.fichier:
            piece.fichier.delete(save=False)
        piece.type_piece, piece.type_contenu, piece.statut, piece.motif_refus = type_piece, type_contenu, 'soumise', ''
        piece.fichier.save(f'piece.{extension}', contenu, save=False)
        piece.save()
        services.piece_a_controler(piece)
        return Response(_piece_json(piece), status=status.HTTP_201_CREATED)


def visites_json(annonces: list[dict]) -> list[dict]:
    """Listings to visit with their host and whether they were already validated once, read in a few queries."""
    hote_ids = {a['host_id'] for a in annonces}
    hotes = {u.pk: u for u in get_user_model().objects.filter(pk__in=hote_ids)}
    pieces = {p.hote_id: p for p in PieceIdentiteModel.objects.filter(hote_id__in=hote_ids)}
    deja_validees = set(VisiteModel.objects.filter(hebergement_id__in=[a['id'] for a in annonces], decision='validee')
                        .values_list('hebergement_id', flat=True))
    resultats = []
    for a in annonces:
        hote = hotes[a['host_id']]
        resultats.append({
            'id': str(a['id']), 'name': a['name'], 'type': a['type'], 'type_libelle': a['type_libelle'],
            'city': a['city'], 'location': a['location'], 'description': a['description'],
            'price_per_night': float(a['price_per_night']), 'max_guests': a['max_guests'], 'amenities': a['amenities'],
            'photos': [u for u in [a['image_url'], *a['images']] if u],
            'modifiee_apres_verification': a['id'] in deja_validees,
            'cree_le': a['created_at'],
            'hote': {
                'id': str(hote.id), 'nom': f"{hote.first_name} {hote.last_name}".strip(), 'email': hote.email,
                'telephone': hote.phone, 'piece': _piece_json(pieces.get(hote.pk)),
            },
        })
    return resultats


def pieces_avec_nb_annonces(pieces) -> list[PieceIdentiteModel]:
    pieces = list(pieces)
    nombres = hebergements.nb_annonces_par_hote(p.hote_id for p in pieces)
    for p in pieces:
        p.nb_annonces = nombres.get(p.hote_id, 0)
    return pieces


class PiecesView(APIView):
    """Identity documents to check remotely, oldest first."""
    permission_classes = [EstVerificateur]

    def get(self, request):
        pieces = pieces_avec_nb_annonces(services.pieces_a_controler().select_related('hote')[:100])
        resultats = [{
            'hote': {
                'id': str(p.hote_id), 'nom': f"{p.hote.first_name} {p.hote.last_name}".strip(),
                'email': p.hote.email, 'telephone': p.hote.phone, 'inscrit_le': p.hote.date_joined,
            },
            'type_piece': p.type_piece, 'type_libelle': p.get_type_piece_display(),
            'soumise_le': p.soumise_le, 'nb_annonces': p.nb_annonces,
        } for p in pieces]
        return Response({'results': resultats, 'count': len(resultats)})


class PieceDecisionView(APIView):
    """POST {decision: verifiee | refusee, motif}: result of the check of a host's identity document."""
    permission_classes = [EstVerificateur]

    def post(self, request, user_id):
        hote = get_user_model().objects.filter(pk=user_id).first()
        if not hote:
            return Response({'detail': 'Hôte introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        decision = str(request.data.get('decision', ''))
        try:
            # In the shared queue: refused if another agent took this document; their mission is closed otherwise
            with transaction.atomic():
                terrain.verifier_peut_decider('piece', hote.pk, request.user)
                piece = services.decider_piece(hote, request.user, decision=decision,
                                               motif=str(request.data.get('motif', '')))
                terrain.terminer('piece', hote.pk, request.user,
                                 decision='validee' if piece.statut == 'verifiee' else 'refusee',
                                 titre=terrain.nom(hote), sous_titre=piece.get_type_piece_display())
        except terrain.MissionErreur as exc:
            return Response({'detail': str(exc)}, status=exc.code)
        except services.VerificationErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        journaliser('identite_verifiee' if piece.statut == 'verifiee' else 'identite_refusee', request,
                    utilisateur=request.user, hote=str(hote.pk), hote_email=hote.email)
        return Response(_piece_json(piece))


class VisitesView(APIView):
    """Listings waiting for an agent's visit, oldest first (?ville= to filter)."""
    permission_classes = [EstVerificateur]

    def get(self, request):
        # Only hosts whose identity is verified (and agreement signed, once required): services.annonces_a_visiter
        annonces = services.annonces_a_visiter(request.query_params.get('ville', '').strip())
        resultats = visites_json(annonces[:100])
        return Response({
            'results': resultats, 'count': len(resultats),
            'controles': VisiteModel.CONTROLES, 'max_photos': services.MAX_PHOTOS_VISITE,
        })


class DecisionView(APIView):
    """POST multipart : decision (validee | refusee), controles (JSON), commentaire, photos (plusieurs)."""
    permission_classes = [EstVerificateur]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        hebergement = hebergements.fiche(pk)
        if not hebergement:
            return Response({'detail': 'Annonce introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        controles = request.data.get('controles') or {}
        if isinstance(controles, str):
            try:
                controles = json.loads(controles)
            except ValueError:
                return Response({'controles': ['Format invalide.']}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(controles, dict):
            return Response({'controles': ['Format invalide.']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # In the shared queue: refused if another agent took this visit; their mission is closed otherwise
            with transaction.atomic():
                terrain.verifier_peut_decider('logement', pk, request.user)
                visite = services.decider(
                    pk, request.user, decision=str(request.data.get('decision', '')), controles=controles,
                    commentaire=str(request.data.get('commentaire', '')), photos=request.FILES.getlist('photos'),
                )
                terrain.terminer('logement', pk, request.user, decision=visite.decision,
                                 titre=hebergement['name'], sous_titre=hebergement['type_libelle'], ville=hebergement['city'])
        except terrain.MissionErreur as exc:
            return Response({'detail': str(exc)}, status=exc.code)
        except (services.VerificationErreur, FichierInvalide) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        journaliser('annonce_verifiee' if visite.decision == 'validee' else 'annonce_refusee', request,
                    utilisateur=request.user, hebergement=str(pk))
        return Response({'decision': visite.decision, 'statut': 'verifiee' if visite.decision == 'validee' else 'refusee'},
                        status=status.HTTP_201_CREATED)


class FichierPieceView(APIView):
    """A host's identity document, read by the API (never a public URL). Every viewing is logged."""
    permission_classes = [EstVerificateur]

    def get(self, request, user_id):
        piece = PieceIdentiteModel.objects.filter(hote_id=user_id).select_related('hote').first()
        if not piece or not piece.fichier:
            raise Http404
        journaliser('piece_consultee', request, utilisateur=request.user, hote=str(piece.hote_id))
        pdf = piece.type_contenu == 'application/pdf'
        reponse = FileResponse(piece.fichier.open('rb'), content_type=piece.type_contenu or 'application/octet-stream',
                               as_attachment=pdf, filename=f"piece-identite.{'pdf' if pdf else 'jpg'}")
        reponse['Cache-Control'] = 'no-store'
        reponse['X-Content-Type-Options'] = 'nosniff'
        # The document cannot run any script, even opened directly in the browser
        reponse['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; sandbox"
        return reponse


class CompteursView(APIView):
    """GET : what waits for an agent, for the badges of the back-office and the agent space (polled every minute)."""
    permission_classes = [EstVerificateur]

    def get(self, request):
        pieces = services.pieces_a_controler().count()
        visites = len(services.annonces_a_visiter())
        return Response({'pieces': pieces, 'visites': visites, 'total': pieces + visites})
