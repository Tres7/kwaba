import math
import uuid

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Count
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.hebergements import api as hebergements
from apps.paiements import api as paiements
from apps.reservations import api as reservations_api

from .models import (
    EtapeModel, LienReservationModel, MembreModel, PropositionModel, VoteModel, VoyageGroupeModel, nouveau_code,
)

MAX_MEMBRES = 20


def _nom(u) -> str:
    return f"{u.first_name} {u.last_name[:1]}.".strip() if u.last_name else u.first_name


def _voyage(pk, user):
    """Trip the user is a member of, or None (404: its existence is not revealed)."""
    return VoyageGroupeModel.objects.filter(pk=pk, membres__utilisateur=user).select_related('organisateur').first()


def _uuid(valeur) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(valeur))
    except (ValueError, TypeError):
        return None


def _entier(valeur) -> int | None:
    try:
        return int(valeur)
    except (ValueError, TypeError):
        return None


def _introuvable():
    return Response({'detail': 'Voyage introuvable.'}, status=status.HTTP_404_NOT_FOUND)


def _reserve_a_l_organisateur():
    return Response({'detail': "Seul l'organisateur du voyage peut faire cela."}, status=status.HTTP_403_FORBIDDEN)


def budget(hebergement, voyage) -> dict | None:
    """Cost of the listing for the trip dates, service fees included, and everyone's share."""
    if not voyage.nuits:
        return None
    total = paiements.total_sejour(hebergement['price_per_night'], voyage.nuits)
    personnes = max(1, voyage.nb_voyageurs)
    return {'nuits': voyage.nuits, 'total': total, 'par_personne': math.ceil(total / personnes), 'personnes': personnes}


def detail(voyage, user, request) -> dict:
    membres = list(voyage.membres.select_related('utilisateur'))
    votes = list(voyage.votes.all())
    mon_vote = next((v.proposition_id for v in votes if v.utilisateur_id == user.id), None)
    liste_propositions = list(voyage.propositions.select_related('propose_par'))
    liens = list(voyage.reservations.select_related('ajoute_par'))
    resas = reservations_api.resumes(lien.reservation_id for lien in liens)
    annonces = hebergements.resumes({p.hebergement_id for p in liste_propositions} | {r['hebergement_id'] for r in resas.values()})
    voyageurs = {u.id: u for u in get_user_model().objects.filter(id__in={r['voyageur_id'] for r in resas.values()})}
    propositions = []
    for p in liste_propositions:
        h = annonces.get(p.hebergement_id)
        if not h:
            continue
        disponible = None
        if voyage.date_debut and voyage.date_fin:
            disponible = h['publiee'] and hebergements.est_disponible(h['id'], voyage.date_debut, voyage.date_fin)
        propositions.append({
            'id': p.id, 'commentaire': p.commentaire, 'propose_par': _nom(p.propose_par),
            'peut_supprimer': user.id in (p.propose_par_id, voyage.organisateur_id),
            'votes': sum(1 for v in votes if v.proposition_id == p.id),
            'votants': [_nom(m.utilisateur) for m in membres if any(v.utilisateur_id == m.utilisateur_id and v.proposition_id == p.id for v in votes)],
            'hebergement': {
                'id': str(h['id']), 'name': h['name'], 'city': h['city'], 'location': h['location'], 'type': h['type'],
                'image_url': h['image_url'], 'price_per_night': float(h['price_per_night']), 'max_guests': h['max_guests'],
                'rating': h['rating'], 'review_count': h['review_count'],
            },
            'budget': budget(h, voyage),
            'disponible': disponible,
            'assez_grand': h['max_guests'] >= voyage.nb_voyageurs,
        })
    propositions.sort(key=lambda p: (-p['votes'], p['id']))
    reservations = []
    for lien in liens:
        r = resas.get(lien.reservation_id)
        h = annonces.get(r['hebergement_id']) if r else None
        if not h:
            continue
        voyageur = voyageurs.get(r['voyageur_id'])
        reservations.append({
            'id': lien.id, 'reservation_id': str(r['id']), 'reference': r['reference'], 'hebergement': h['name'],
            'hebergement_id': str(h['id']), 'ville': h['city'], 'adresse': h['location'],
            'check_in': r['check_in'], 'check_out': r['check_out'], 'voyageurs': r['voyageurs'], 'statut': r['statut'],
            'total': float(r['total']), 'reserve_par': _nom(voyageur) if voyageur else '',
            'peut_retirer': user.id in (lien.ajoute_par_id, voyage.organisateur_id),
        })
    return {
        'id': voyage.id, 'nom': voyage.nom, 'destination': voyage.destination,
        'date_debut': voyage.date_debut, 'date_fin': voyage.date_fin, 'nuits': voyage.nuits,
        'nb_voyageurs': voyage.nb_voyageurs, 'notes': voyage.notes,
        'organisateur': _nom(voyage.organisateur), 'est_organisateur': voyage.organisateur_id == user.id,
        'code_invitation': voyage.code_invitation,
        'membres': [{'id': m.utilisateur_id, 'nom': _nom(m.utilisateur), 'organisateur': m.utilisateur_id == voyage.organisateur_id,
                     'moi': m.utilisateur_id == user.id} for m in membres],
        'propositions': propositions,
        'mon_vote': mon_vote,
        'proposition_retenue': voyage.proposition_retenue_id,
        'etapes': [{
            'id': e.id, 'date': e.date, 'heure': e.heure.strftime('%H:%M') if e.heure else None, 'titre': e.titre,
            'lieu': e.lieu, 'details': e.details, 'ajoute_par': _nom(e.ajoute_par),
            'peut_supprimer': user.id in (e.ajoute_par_id, voyage.organisateur_id),
        } for e in voyage.etapes.select_related('ajoute_par')],
        'reservations': reservations,
        'mis_a_jour_le': voyage.mis_a_jour_le,
    }


class VoyageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoyageGroupeModel
        fields = ['nom', 'destination', 'date_debut', 'date_fin', 'nb_voyageurs', 'notes']
        extra_kwargs = {'nb_voyageurs': {'min_value': 1, 'max_value': MAX_MEMBRES}}

    def validate(self, data):
        debut = data.get('date_debut', getattr(self.instance, 'date_debut', None))
        fin = data.get('date_fin', getattr(self.instance, 'date_fin', None))
        if debut and fin and fin <= debut:
            raise serializers.ValidationError({'date_fin': "La date de retour doit être après la date d'arrivée."})
        if (debut is None) != (fin is None):
            raise serializers.ValidationError({'date_fin': "Indiquez les deux dates, ou aucune."})
        return data


class VoyagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        voyages = (VoyageGroupeModel.objects.filter(membres__utilisateur=request.user)
                   .select_related('organisateur').annotate(nb_membres=Count('membres', distinct=True),
                                                            nb_propositions=Count('propositions', distinct=True)))
        return Response({'results': [{
            'id': v.id, 'nom': v.nom, 'destination': v.destination, 'date_debut': v.date_debut, 'date_fin': v.date_fin,
            'nb_membres': v.nb_membres, 'nb_propositions': v.nb_propositions, 'organisateur': _nom(v.organisateur),
            'est_organisateur': v.organisateur_id == request.user.id,
        } for v in voyages]})

    def post(self, request):
        serializer = VoyageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            voyage = serializer.save(organisateur=request.user)
            MembreModel.objects.create(voyage=voyage, utilisateur=request.user)
        return Response(detail(voyage, request.user, request), status=status.HTTP_201_CREATED)


class VoyageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        voyage = _voyage(pk, request.user)
        return Response(detail(voyage, request.user, request)) if voyage else _introuvable()

    def patch(self, request, pk):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        # Any member can add to the shared notes; the rest is reserved for the organiser
        if set(request.data) - {'notes'} and voyage.organisateur_id != request.user.id:
            return _reserve_a_l_organisateur()
        serializer = VoyageSerializer(voyage, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(detail(voyage, request.user, request))

    def delete(self, request, pk):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        if voyage.organisateur_id != request.user.id:
            return _reserve_a_l_organisateur()
        voyage.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvitationView(APIView):
    """GET: preview before joining; POST: join the trip."""
    permission_classes = [IsAuthenticated]

    def _par_code(self, code):
        return VoyageGroupeModel.objects.filter(code_invitation=code).select_related('organisateur').first()

    def get(self, request, code):
        voyage = self._par_code(code)
        if not voyage:
            return Response({'detail': "Ce lien d'invitation n'est plus valable."}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'id': voyage.id, 'nom': voyage.nom, 'destination': voyage.destination, 'date_debut': voyage.date_debut,
            'date_fin': voyage.date_fin, 'organisateur': _nom(voyage.organisateur), 'nb_membres': voyage.membres.count(),
            'deja_membre': voyage.membres.filter(utilisateur=request.user).exists(),
        })

    def post(self, request, code):
        voyage = self._par_code(code)
        if not voyage:
            return Response({'detail': "Ce lien d'invitation n'est plus valable."}, status=status.HTTP_404_NOT_FOUND)
        if not voyage.membres.filter(utilisateur=request.user).exists():
            if voyage.membres.count() >= MAX_MEMBRES:
                return Response({'detail': f"Ce voyage a atteint {MAX_MEMBRES} membres."}, status=status.HTTP_400_BAD_REQUEST)
            MembreModel.objects.get_or_create(voyage=voyage, utilisateur=request.user)
        return Response({'id': voyage.id})


class NouveauLienView(APIView):
    """The organiser invalidates the old invitation link (link shared by mistake…)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        if voyage.organisateur_id != request.user.id:
            return _reserve_a_l_organisateur()
        voyage.code_invitation = nouveau_code()
        voyage.save(update_fields=['code_invitation', 'mis_a_jour_le'])
        return Response({'code_invitation': voyage.code_invitation})


class MembreView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, user_id):
        """Leave the trip (oneself) or remove a member (organiser)."""
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        if str(user_id) != str(request.user.id) and voyage.organisateur_id != request.user.id:
            return _reserve_a_l_organisateur()
        if str(user_id) == str(voyage.organisateur_id):
            return Response({'detail': "L'organisateur ne peut pas quitter le voyage : supprimez-le plutôt."},
                            status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            VoteModel.objects.filter(voyage=voyage, utilisateur_id=user_id).delete()
            MembreModel.objects.filter(voyage=voyage, utilisateur_id=user_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PropositionsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        hebergement_id = _uuid(request.data.get('hebergement'))
        if not hebergement_id or not hebergements.est_publiee(hebergement_id):
            return Response({'hebergement': ['Logement introuvable.']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():  # the duplicate must not break the request's transaction
                PropositionModel.objects.create(
                    voyage=voyage, hebergement_id=hebergement_id, propose_par=request.user,
                    commentaire=str(request.data.get('commentaire', ''))[:280],
                )
        except IntegrityError:
            return Response({'detail': 'Ce logement est déjà proposé au groupe.'}, status=status.HTTP_409_CONFLICT)
        voyage.save(update_fields=['mis_a_jour_le'])
        return Response(detail(voyage, request.user, request), status=status.HTTP_201_CREATED)


class PropositionView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, proposition_id):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        p = voyage.propositions.filter(pk=proposition_id).first()
        if not p:
            return Response({'detail': 'Proposition introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.id not in (p.propose_par_id, voyage.organisateur_id):
            return Response({'detail': "Seul l'auteur de la proposition ou l'organisateur peut la retirer."},
                            status=status.HTTP_403_FORBIDDEN)
        p.delete()
        voyage.save(update_fields=['mis_a_jour_le'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class VoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        proposition = voyage.propositions.filter(pk=_entier(request.data.get('proposition'))).first()
        if not proposition:
            return Response({'proposition': ['Proposition introuvable.']}, status=status.HTTP_400_BAD_REQUEST)
        VoteModel.objects.update_or_create(voyage=voyage, utilisateur=request.user, defaults={'proposition': proposition})
        voyage.save(update_fields=['mis_a_jour_le'])
        return Response(detail(voyage, request.user, request))

    def delete(self, request, pk):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        VoteModel.objects.filter(voyage=voyage, utilisateur=request.user).delete()
        voyage.save(update_fields=['mis_a_jour_le'])
        return Response(detail(voyage, request.user, request))


class RetenirView(APIView):
    """The organiser settles the choice of the listing (or cancels it with `proposition: null`)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        if voyage.organisateur_id != request.user.id:
            return _reserve_a_l_organisateur()
        pid = request.data.get('proposition')
        proposition = voyage.propositions.filter(pk=_entier(pid)).first() if pid else None
        if pid and not proposition:
            return Response({'proposition': ['Proposition introuvable.']}, status=status.HTTP_400_BAD_REQUEST)
        voyage.proposition_retenue = proposition
        voyage.save(update_fields=['proposition_retenue', 'mis_a_jour_le'])
        return Response(detail(voyage, request.user, request))


class EtapeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtapeModel
        fields = ['date', 'heure', 'titre', 'lieu', 'details']


class EtapesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        serializer = EtapeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(voyage=voyage, ajoute_par=request.user)
        voyage.save(update_fields=['mis_a_jour_le'])
        return Response(detail(voyage, request.user, request), status=status.HTTP_201_CREATED)


class EtapeView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, etape_id):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        etape = voyage.etapes.filter(pk=etape_id).first()
        if not etape:
            return Response({'detail': 'Étape introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.id not in (etape.ajoute_par_id, voyage.organisateur_id):
            return Response({'detail': "Seul l'auteur de l'étape ou l'organisateur peut la supprimer."},
                            status=status.HTTP_403_FORBIDDEN)
        etape.delete()
        voyage.save(update_fields=['mis_a_jour_le'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReservationsPartageesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        # Only one's own bookings can be shared
        reservation_id = _uuid(request.data.get('reservation'))
        if not reservation_id or not reservations_api.appartient_au_voyageur(reservation_id, request.user.id):
            return Response({'reservation': ['Réservation introuvable.']}, status=status.HTTP_400_BAD_REQUEST)
        LienReservationModel.objects.get_or_create(voyage=voyage, reservation_id=reservation_id,
                                                   defaults={'ajoute_par': request.user})
        voyage.save(update_fields=['mis_a_jour_le'])
        return Response(detail(voyage, request.user, request), status=status.HTTP_201_CREATED)


class ReservationPartageeView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, lien_id):
        voyage = _voyage(pk, request.user)
        if not voyage:
            return _introuvable()
        lien = voyage.reservations.filter(pk=lien_id).first()
        if not lien:
            return Response({'detail': 'Réservation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.id not in (lien.ajoute_par_id, voyage.organisateur_id):
            return Response({'detail': "Seul la personne qui l'a partagée ou l'organisateur peut la retirer."},
                            status=status.HTTP_403_FORBIDDEN)
        lien.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
