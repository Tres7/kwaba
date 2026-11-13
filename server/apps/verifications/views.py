import json

from django.db import transaction
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.hebergements import api as hebergements
from apps.activity import api as activity
from apps.securite.permissions import a_acces_section
from apps.terrain import api as terrain
from apps.users import api as users

from . import services
from .fichiers import FichierInvalide, piece_identite
from .models import PieceIdentiteModel, VisiteModel


class EstVerificateur(IsAuthenticated):
    """Field agents and administrators: role read from the database at every request."""
    message = "Réservé aux agents de vérification."

    def has_permission(self, request, view):
        if not (super().has_permission(request, view) and request.user.role in services.ROLES_VERIFICATEURS):
            return False
        return request.user.role != 'admin' or a_acces_section(request.user, 'verifications')


def _piece_json(piece: PieceIdentiteModel | None) -> dict:
    if not piece:
        return {'statut': 'absente'}
    return {
        'statut': piece.statut, 'type_piece': piece.type_piece, 'type_libelle': piece.get_type_piece_display(),
        'soumise_le': piece.soumise_le, 'verifiee_le': piece.verifiee_le, 'motif_refus': piece.motif_refus,
        # False for the documents verified before they were kept (deleted then): the agent asks for the original
        'copie': bool(piece.fichier),
    }


class MaPieceIdentiteView(APIView):
    """GET: status of my identity document. POST (multipart type_piece, fichier): send or replace it."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_scope = 'verification_piece'

    def get_throttles(self):
        return [ScopedRateThrottle()] if self.request.method == 'POST' else []

    def get(self, request):
        return Response(_piece_json(PieceIdentiteModel.objects.filter(hote_id=request.user.pk).first()))

    def post(self, request):
        if not users.peut_gerer_annonces(request.user):
            return Response({'detail': 'Réservé aux hôtes.'}, status=status.HTTP_403_FORBIDDEN)
        type_piece = request.data.get('type_piece')
        if type_piece not in dict(PieceIdentiteModel.TYPES):
            return Response({'type_piece': ["Choisissez le type de pièce."]}, status=status.HTTP_400_BAD_REQUEST)
        fichier = request.FILES.get('fichier')
        if not fichier:
            return Response({'fichier': ['Aucun fichier reçu.']}, status=status.HTTP_400_BAD_REQUEST)

        piece = PieceIdentiteModel.objects.filter(hote_id=request.user.pk).first()
        if piece and piece.statut == 'verifiee':
            return Response({'detail': 'Votre identité est déjà vérifiée.'}, status=status.HTTP_409_CONFLICT)
        try:
            contenu, extension, type_contenu = piece_identite(fichier)
        except FichierInvalide as exc:
            return Response({'fichier': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        piece = piece or PieceIdentiteModel(hote_id=request.user.pk)
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
    hotes = users.comptes(hote_ids)
    pieces = {p.hote_id: p for p in PieceIdentiteModel.objects.filter(hote_id__in=hote_ids)}
    deja_validees = set(VisiteModel.objects.filter(hebergement_id__in=[a['id'] for a in annonces], decision='validee')
                        .values_list('hebergement_id', flat=True))
    resultats = []
    for a in annonces:
        hote = hotes[a['host_id']]
        resultats.append({
            'id': str(a['id']), 'name': a['name'], 'type': a['type'], 'type_libelle': a['type_libelle'],
            'city': a['city'], 'location': a['location'], 'point_repere': a['point_repere'], 'description': a['description'],
            'position': {'lat': float(a['latitude']), 'lng': float(a['longitude'])} if a['latitude'] is not None else None,
            'price_per_night': float(a['price_per_night']), 'max_guests': a['max_guests'], 'amenities': a['amenities'],
            'photos': [u for u in [a['image_url'], *a['images']] if u], 'legendes_photos': a['legendes_photos'],
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
    hotes = users.comptes(p.hote_id for p in pieces)
    for p in pieces:
        p.nb_annonces = nombres.get(p.hote_id, 0)
        p.compte_hote = hotes.get(p.hote_id)
    return pieces


class PiecesView(APIView):
    """Identity documents to check remotely, oldest first."""
    permission_classes = [EstVerificateur]

    def get(self, request):
        pieces = pieces_avec_nb_annonces(services.pieces_a_controler()[:100])
        resultats = [{
            'hote': {
                'id': str(p.hote_id), 'nom': p.compte_hote.get_full_name(),
                'email': p.compte_hote.email, 'telephone': p.compte_hote.phone, 'inscrit_le': p.compte_hote.date_joined,
            },
            'type_piece': p.type_piece, 'type_libelle': p.get_type_piece_display(),
            'soumise_le': p.soumise_le, 'nb_annonces': p.nb_annonces,
        } for p in pieces]
        return Response({'results': resultats, 'count': len(resultats)})


class PieceDecisionView(APIView):
    """POST {decision: verifiee | refusee, motif}: result of the check of a host's identity document."""
    permission_classes = [EstVerificateur]

    def post(self, request, user_id):
        hote = users.compte(user_id)
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
        activity.record('identite_verifiee' if piece.statut == 'verifiee' else 'identite_refusee', request,
                        actor=request.user, hote=str(hote.pk), hote_email=hote.email)
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
                    position={k: request.data[k] for k in ('latitude', 'longitude', 'precision') if request.data.get(k)} or None,
                    early_reason=str(request.data.get('early_reason', '')),
                )
                terrain.terminer('logement', pk, request.user, decision=visite.decision,
                                 titre=hebergement['name'], sous_titre=hebergement['type_libelle'], ville=hebergement['city'])
        except terrain.MissionErreur as exc:
            return Response({'detail': str(exc)}, status=exc.code)
        except (services.VerificationErreur, FichierInvalide) as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        activity.record('annonce_verifiee' if visite.decision == 'validee' else 'annonce_refusee', request,
                        actor=request.user, hebergement=str(pk), annonce=hebergement['name'])
        if visite.decision == 'validee' and visite.latitude is not None:
            # The agent's position replaces the host's point: traced with the gap, to spot hosts who misplace theirs
            activity.record('position_corrigee', request, actor=request.user, hebergement=str(pk),
                            annonce=hebergement['name'], source='visite', ecart_m=visite.ecart_m,
                            precision_m=visite.precision_m)
        return Response({'decision': visite.decision, 'statut': 'verifiee' if visite.decision == 'validee' else 'refusee'},
                        status=status.HTTP_201_CREATED)


class PhotosDecisionView(APIView):
    """POST {retirer: [url], motif}: the photos added to a verified listing are checked; the ones listed leave it."""
    permission_classes = [EstVerificateur]

    def post(self, request, pk):
        annonce = hebergements.fiche(pk)
        if not annonce:
            return Response({'detail': 'Annonce introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        retirer = request.data.get('retirer') or []
        if not isinstance(retirer, list) or not all(isinstance(u, str) for u in retirer):
            return Response({'retirer': ['Liste de photos attendue.']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                terrain.verifier_peut_decider('photos', pk, request.user)
                resultat = services.decider_photos(pk, request.user, retirer=retirer,
                                                   motif=str(request.data.get('motif', '')))
                nombre = len(resultat['retirees'])
                terrain.terminer('photos', pk, request.user, decision='validee', titre=annonce['name'],
                                 sous_titre=f"{nombre} photo(s) retirée(s)" if nombre else 'Photos gardées',
                                 ville=annonce['city'])
        except terrain.MissionErreur as exc:
            return Response({'detail': str(exc)}, status=exc.code)
        except services.VerificationErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        activity.record('photos_controlees', request, actor=request.user, hebergement=str(pk),
                        annonce=annonce['name'], retirees=len(resultat['retirees']))
        return Response({'retirees': resultat['retirees'], 'images': resultat['images']})


class FichierPieceView(APIView):
    """A host's identity document, read by the API (never a public URL). Every viewing is logged."""
    permission_classes = [EstVerificateur]

    def get(self, request, user_id):
        piece = PieceIdentiteModel.objects.filter(hote_id=user_id).first()
        if not piece or not piece.fichier:
            raise Http404
        if not piece.fichier.storage.exists(piece.fichier.name):
            # Lost (private files deleted by a deployment before the prive-data volume)
            if piece.statut == 'verifiee':
                detail = "Ce fichier est perdu. Lors de la visite, demandez à l'hôte de vous montrer l'original."
            else:
                detail = ("Ce fichier est perdu. Refusez la pièce avec un motif qui demande à l'hôte de la renvoyer : "
                          "il sera prévenu par email.")
            return Response({'detail': detail}, status=status.HTTP_410_GONE)
        activity.record('piece_consultee', request, actor=request.user, hote=str(piece.hote_id))
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
        photos = len(services.annonces_photos_a_controler())
        return Response({'pieces': pieces, 'visites': visites, 'photos': photos, 'total': pieces + visites + photos})


class PositionsView(APIView):
    """GET ?q=&toutes=1: verified listings whose position an agent can correct (by default, those still at the host's
    point), with the number left to measure."""
    permission_classes = [EstVerificateur]

    def get(self, request):
        q = request.query_params.get('q', '').strip()[:100]
        toutes = request.query_params.get('toutes') in ('1', 'true')
        annonces = hebergements.annonces_pour_position(q, a_relever=not toutes,
                                                       hote_ids=users.ids_par_recherche(q) if q else ())
        hotes = users.comptes({a['host_id'] for a in annonces})
        return Response({
            'a_relever': hebergements.nb_positions_a_relever(),
            'results': [{
                'id': str(a['id']), 'name': a['name'], 'type_libelle': a['type_libelle'], 'city': a['city'],
                'location': a['location'], 'point_repere': a['point_repere'],
                'position': {'lat': float(a['latitude']), 'lng': float(a['longitude'])} if a['latitude'] is not None else None,
                'position_relevee_le': a['position_relevee_le'],
                'hote': {'nom': f"{h.first_name} {h.last_name}".strip(), 'telephone': h.phone}
                if (h := hotes.get(a['host_id'])) else None,
            } for a in annonces],
        })


class LirePositionView(APIView):
    """POST {texte}: latitude and longitude of a pasted Google Maps link, WhatsApp location or coordinates."""
    permission_classes = [EstVerificateur]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'verification_position'

    def post(self, request):
        try:
            latitude, longitude = services.lire_position(str(request.data.get('texte', '')))
        except services.VerificationErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'latitude': float(latitude), 'longitude': float(longitude)})


class CorrectionPositionView(APIView):
    """POST {latitude, longitude, precision?, source: gps | texte}: the position of a verified listing is replaced; it
    stays online. Traced with the gap from the previous point."""
    permission_classes = [EstVerificateur]

    def post(self, request, pk):
        annonce = hebergements.fiche(pk)
        if not annonce:
            return Response({'detail': 'Annonce introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        source = str(request.data.get('source', ''))
        try:
            resultat = services.corriger_position(
                pk, request.user, latitude=request.data.get('latitude'), longitude=request.data.get('longitude'),
                precision=request.data.get('precision'), source=source,
            )
        except services.VerificationErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        activity.record('position_corrigee', request, actor=request.user, hebergement=str(pk),
                        annonce=annonce['name'], source=source, ecart_m=resultat['ecart_m'],
                        precision_m=resultat['precision_m'])
        return Response({**resultat, 'latitude': float(resultat['latitude']), 'longitude': float(resultat['longitude'])})
