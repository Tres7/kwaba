"""Back-office API. Contract: documentation/modules/backoffice-api.md.

Every view requires the admin role, read from the database at every request (EstAdministrateur). Every write is
recorded in the audit log (apps.securite) with the administrator, the target and the reason.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.avis.models import AvisModel
from apps.hebergements import api as hebergements
from apps.hebergements.archivage import ArchivageImpossible, archiver, restaurer
from apps.hebergements.models import HebergementModel
from apps.paiements import services as paiements, tarifs
from apps.paiements.models import ConditionsHoteModel
from apps.reservations import api as reservations_api
from apps.reservations.models import ReservationModel
from apps.securite.audit import journaliser
from apps.securite.backoffice import paginer as _paginer
from apps.securite.permissions import EstAdministrateur
from apps.users.infrastructure.http.controllers.AuthController import revoquer_jetons
from apps.verifications import api as verifications

User = get_user_model()

ROLES = [code for code, _ in User.ROLE_CHOICES]
MOTIF_MIN, MOTIF_MAX = 5, 500


# --- Outils communs ---------------------------------------------------------------------------------

def _entier(valeur, defaut: int, minimum: int = 1, maximum: int | None = None) -> int:
    try:
        nombre = int(valeur)
    except (TypeError, ValueError):
        return defaut
    nombre = max(nombre, minimum)
    return min(nombre, maximum) if maximum else nombre


def _booleen(valeur):
    """'true' / 'false' (URL parameter) → bool; any other value → None (filter ignored)."""
    return {'true': True, 'false': False}.get((valeur or '').lower())


def _motif(valeur):
    """Required reason for deletions and cancellations: (reason, error response or None)."""
    motif = (valeur or '').strip()
    if not MOTIF_MIN <= len(motif) <= MOTIF_MAX:
        return motif, Response(
            {'motif': [f'Indiquez un motif de {MOTIF_MIN} à {MOTIF_MAX} caractères.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return motif, None


def _nom(utilisateur) -> str:
    return f'{utilisateur.first_name} {utilisateur.last_name}'.strip() or utilisateur.email


def _introuvable(quoi: str) -> Response:
    return Response({'detail': f'{quoi} introuvable.'}, status=status.HTTP_404_NOT_FOUND)


class VueAdmin(APIView):
    permission_classes = [EstAdministrateur]


# --- 1. Tableau de bord -----------------------------------------------------------------------------

class StatsView(VueAdmin):
    def get(self, request):
        maintenant = timezone.now()
        aujourd_hui = timezone.localdate()
        premier_jour = aujourd_hui - timedelta(days=29)
        il_y_a_30j = maintenant - timedelta(days=30)

        utilisateurs = User.objects.aggregate(
            total=Count('id'),
            nouveaux_30j=Count('id', filter=Q(date_joined__gte=il_y_a_30j)),
            hotes=Count('id', filter=Q(role='hote')),
            desactives=Count('id', filter=Q(is_active=False)),
        )
        annonces = HebergementModel.objects.aggregate(
            total=Count('id'),
            visibles=Count('id', filter=Q(is_available=True, statut_verification='verifiee')),
            verifiees=Count('id', filter=Q(statut_verification='verifiee')),
            # Waiting for an agent's visit (refused listings wait for the host, not for an agent)
            en_attente=Count('id', filter=Q(statut_verification='en_attente')),
        )
        recentes = ReservationModel.objects.filter(created_at__gte=il_y_a_30j)
        reservations = recentes.aggregate(
            confirmees_30j=Count('id', filter=Q(status='confirmed')),
            annulees_30j=Count('id', filter=Q(status='cancelled')),
            volume_30j=Sum('total_price', filter=Q(status='confirmed')),
        )
        reservations['volume_30j'] = int(reservations['volume_30j'] or 0)
        avis = AvisModel.objects.aggregate(total=Count('id'), moyenne=Avg('note'))
        avis['moyenne'] = round(avis['moyenne'], 1) if avis['moyenne'] is not None else None

        # One entry per day over 30 days (today included), 0 on days without a confirmed booking
        par_jour = {
            ligne['jour']: ligne
            for ligne in ReservationModel.objects
            .filter(status='confirmed', created_at__date__gte=premier_jour)
            .annotate(jour=TruncDate('created_at'))
            .values('jour')
            .annotate(nombre=Count('id'), volume=Sum('total_price'))
        }
        serie = []
        for decalage in range(30):
            jour = premier_jour + timedelta(days=decalage)
            ligne = par_jour.get(jour, {})
            serie.append({'date': jour.isoformat(), 'nombre': ligne.get('nombre', 0), 'volume': int(ligne.get('volume') or 0)})

        return Response({
            'utilisateurs': utilisateurs,
            'annonces': annonces,
            'reservations': reservations,
            'avis': avis,
            'reservations_par_jour': serie,
        })


# --- 2. Utilisateurs --------------------------------------------------------------------------------

def _conditions(u) -> dict | None:
    """Host's commission: category, Founders Programme and rate applied today."""
    if u.role != 'hote':
        return None
    c = getattr(u, 'conditions_hote', None)
    return {
        'categorie': c.categorie if c else 'particulier',
        'fondateur_debut': c.fondateur_debut if c else None,
        'fondateur_fin': c.fondateur_fin if c else None,
        'commission_pourcent': float(tarifs.taux_commission(u) * 100),
    }


def _utilisateur(u) -> dict:
    return {
        'id': str(u.id), 'email': u.email, 'first_name': u.first_name, 'last_name': u.last_name,
        'role': u.role, 'phone': u.phone, 'avatar_url': u.avatar.url if u.avatar else None,
        'is_verified': u.is_verified, 'is_active': u.is_active,
        'date_joined': u.date_joined, 'last_login': u.last_login,
        'nb_reservations': u.nb_reservations, 'nb_annonces': u.nb_annonces,
        'conditions': _conditions(u),
    }


def _utilisateurs():
    return User.objects.select_related('conditions_hote').annotate(
        nb_reservations=Count('reservations', distinct=True),
        nb_annonces=Count('hebergements', distinct=True),
    ).order_by('-date_joined')


class UtilisateurListView(VueAdmin):
    def get(self, request):
        qs = _utilisateurs()
        params = request.query_params
        if q := params.get('q', '').strip():
            qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone__icontains=q))
        if (role := params.get('role')) in ROLES:
            qs = qs.filter(role=role)
        if (actif := _booleen(params.get('actif'))) is not None:
            qs = qs.filter(is_active=actif)
        return _paginer(request, qs, _utilisateur)


class UtilisateurDetailView(VueAdmin):
    def patch(self, request, pk):
        if str(pk) == str(request.user.pk):
            return Response({'detail': 'Vous ne pouvez pas modifier votre propre compte.'}, status=status.HTTP_403_FORBIDDEN)
        cible = User.objects.filter(pk=pk).first()
        if not cible:
            return _introuvable('Utilisateur')

        donnees = request.data
        role = donnees.get('role')
        if 'role' in donnees and role not in ROLES:
            return Response({'role': [f"Rôle invalide : {', '.join(ROLES)}."]}, status=status.HTTP_400_BAD_REQUEST)
        actif = donnees.get('is_active')
        if 'is_active' in donnees and not isinstance(actif, bool):
            return Response({'is_active': ['Valeur booléenne attendue.']}, status=status.HTTP_400_BAD_REQUEST)

        trace = {'cible_id': str(cible.pk), 'cible_email': cible.email}
        if 'role' in donnees and role != cible.role:
            journaliser('role_modifie', request, utilisateur=request.user, avant=cible.role, apres=role, **trace)
            cible.role = role
        if 'is_active' in donnees and actif != cible.is_active:
            cible.is_active = actif
            journaliser('compte_desactive' if not actif else 'compte_reactive', request, utilisateur=request.user, **trace)
        if 'conditions' in donnees:
            erreur = _modifier_conditions(cible, donnees.get('conditions'), request)
            if erreur:
                return Response({'conditions': [erreur]}, status=status.HTTP_400_BAD_REQUEST)
        cible.save(update_fields=['role', 'is_active'])
        if not cible.is_active:
            # Closes their sessions: without a valid refresh token, they are signed out at the latest when the access token expires
            revoquer_jetons(cible.pk)
        return Response(_utilisateur(_utilisateurs().get(pk=cible.pk)))


def _modifier_conditions(cible, valeurs, request) -> str | None:
    """Category (individual, hotel) and Founders Programme dates of a host. Returns an error message."""
    if cible.role != 'hote' or not isinstance(valeurs, dict):
        return "Seul un hôte a des conditions de commission."
    categorie = valeurs.get('categorie', 'particulier')
    if categorie not in dict(ConditionsHoteModel.CATEGORIES):
        return "Catégorie inconnue."
    debut, fin = (parse_date(str(valeurs.get(c) or '')) or None for c in ('fondateur_debut', 'fondateur_fin'))
    if bool(debut) != bool(fin):
        return "Indiquez le début et la fin du Programme Fondateurs, ou aucun des deux."
    if debut and fin <= debut:
        return "La fin du Programme Fondateurs doit être après son début."
    if debut and categorie == 'hotel':
        return "Le Programme Fondateurs concerne les hôtes particuliers."
    if debut and not ConditionsHoteModel.objects.filter(hote=cible, fondateur_debut__isnull=False).exists() \
            and ConditionsHoteModel.objects.filter(fondateur_debut__isnull=False).count() >= FONDATEURS_MAX:
        return f"Le Programme Fondateurs est limité aux {FONDATEURS_MAX} premiers hôtes."
    ConditionsHoteModel.objects.update_or_create(hote=cible, defaults={
        'categorie': categorie, 'fondateur_debut': debut, 'fondateur_fin': fin, 'mis_a_jour_par': request.user})
    journaliser('backoffice_modification', request, utilisateur=request.user, objet='conditions_hote', id=str(cible.pk),
                champs=['categorie', 'fondateur_debut', 'fondateur_fin'])
    return None


FONDATEURS_MAX = 50


# --- 3. Annonces ------------------------------------------------------------------------------------

def _hebergements_json(liste) -> list[dict]:
    nb_reservations = reservations_api.nb_par_annonce(h.id for h in liste)
    return [{
        'id': str(h.id), 'name': h.name, 'type': h.type, 'city': h.city, 'location': h.location,
        'price_per_night': h.price_per_night, 'image_url': h.image_url, 'is_available': h.is_available,
        'est_verifie': h.statut_verification == 'verifiee', 'statut_verification': h.statut_verification,
        'rating': h.rating, 'review_count': h.review_count, 'nb_reservations': nb_reservations.get(h.id, 0),
        'host': {'id': str(h.host_id), 'nom': _nom(h.host), 'email': h.host.email},
        'created_at': h.created_at, 'archivee_le': h.archivee_le,
    } for h in liste]


def _hebergement(h) -> dict:
    return _hebergements_json([h])[0]


def _hebergements(archivees=False):
    qs = HebergementModel.tous.filter(archivee_le__isnull=False) if archivees else HebergementModel.objects.all()
    return qs.select_related('host').order_by('-created_at')


class HebergementListView(VueAdmin):
    def get(self, request):
        params = request.query_params
        qs = _hebergements(archivees=_booleen(params.get('archivees')) is True)
        if q := params.get('q', '').strip():
            qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q) | Q(location__icontains=q) | Q(host__email__icontains=q))
        if ville := params.get('ville', '').strip():
            qs = qs.filter(city__iexact=ville)
        if (visible := _booleen(params.get('visible'))) is not None:
            qs = qs.filter(is_available=visible)
        if (verifie := _booleen(params.get('verifie'))) is not None:
            qs = qs.filter(statut_verification='verifiee') if verifie else qs.exclude(statut_verification='verifiee')
        if (statut := params.get('statut', '')) in dict(HebergementModel.STATUTS_VERIFICATION):
            qs = qs.filter(statut_verification=statut)
        return _paginer(request, qs, _hebergements_json, en_lot=True)


class HebergementDetailView(VueAdmin):
    def patch(self, request, pk):
        annonce = HebergementModel.objects.select_related('host').filter(pk=pk).first()
        if not annonce:
            return _introuvable('Annonce')

        donnees = request.data
        for champ in ('is_available', 'est_verifie'):
            if champ in donnees and not isinstance(donnees[champ], bool):
                return Response({champ: ['Valeur booléenne attendue.']}, status=status.HTTP_400_BAD_REQUEST)

        changements = {}
        if 'is_available' in donnees and donnees['is_available'] != annonce.is_available:
            changements['is_available'] = annonce.is_available = donnees['is_available']
        a_verifier = False
        if 'est_verifie' in donnees and donnees['est_verifie'] != (annonce.statut_verification == 'verifiee'):
            # Validating here publishes the listing without an agent visit; removing the validation takes it off the site
            # and tells the agents that a visit is needed
            annonce.statut_verification = 'verifiee' if donnees['est_verifie'] else 'en_attente'
            if donnees['est_verifie']:
                annonce.motif_refus = ''
            changements['statut_verification'] = annonce.statut_verification
            a_verifier = not donnees['est_verifie']

        if changements:
            annonce.save()
            journaliser('annonce_modifiee', request, utilisateur=request.user,
                        annonce_id=str(annonce.pk), annonce=annonce.name, **changements)
            if a_verifier:
                verifications.visite_a_planifier(annonce.id)
        return Response(_hebergement(_hebergements().get(pk=annonce.pk)))

    def delete(self, request, pk):
        motif, erreur = _motif(request.query_params.get('motif'))
        if erreur:
            return erreur
        annonce = HebergementModel.objects.select_related('host').filter(pk=pk).first()
        if not annonce:
            return _introuvable('Annonce')
        trace = {'annonce_id': str(annonce.pk), 'annonce': annonce.name, 'hote': annonce.host.email, 'motif': motif}
        try:
            archiver(annonce)
        except ArchivageImpossible as e:
            return Response({'detail': str(e)}, status=status.HTTP_409_CONFLICT)
        journaliser('annonce_supprimee', request, utilisateur=request.user, **trace)
        return Response(status=status.HTTP_204_NO_CONTENT)


class HebergementRestaurerView(VueAdmin):
    def post(self, request, pk):
        annonce = HebergementModel.tous.select_related('host').filter(pk=pk, archivee_le__isnull=False).first()
        if not annonce:
            return _introuvable('Annonce archivée')
        restaurer(annonce)
        journaliser('annonce_restauree', request, utilisateur=request.user, annonce_id=str(annonce.pk),
                    annonce=annonce.name, hote=annonce.host.email)
        return Response(_hebergement(_hebergements().get(pk=annonce.pk)))


# --- 4. Bookings --------------------------------------------------------------------------------

def _reservations_json(liste) -> list[dict]:
    annonces = hebergements.resumes({r.hebergement_id for r in liste})
    hotes = {u.pk: u for u in User.objects.filter(pk__in={a['host_id'] for a in annonces.values()})}
    resultats = []
    for r in liste:
        h = annonces.get(r.hebergement_id, {})
        hote = hotes.get(h.get('host_id'))
        resultats.append({
            'id': str(r.id), 'reference': r.reference,
            'hebergement': {'id': str(r.hebergement_id), 'name': h.get('name', ''), 'city': h.get('city', '')},
            'voyageur': {'id': str(r.guest_id), 'nom': _nom(r.guest), 'email': r.guest.email},
            'hote': {'id': str(h['host_id']) if h else '', 'nom': _nom(hote) if hote else ''},
            'check_in': r.check_in, 'check_out': r.check_out, 'nights': r.nights, 'guests_count': r.guests_count,
            'total_price': int(r.total_price), 'status': r.status, 'payment_method': r.payment_method,
            'created_at': r.created_at,
        })
    return resultats


def _reservation(r) -> dict:
    return _reservations_json([r])[0]


def _reservations():
    return ReservationModel.objects.select_related('guest').order_by('-created_at')


class ReservationListView(VueAdmin):
    def get(self, request):
        qs = _reservations()
        params = request.query_params
        if q := params.get('q', '').strip():
            filtre = Q(hebergement_id__in=hebergements.ids_par_nom(q)) | Q(guest__email__icontains=q)
            # Reference RES-AF2026-3A43: the last 4 characters are the start of the id
            if q.upper().startswith('RES-'):
                fin = q.rsplit('-', 1)[-1]
                if len(fin) >= 2:
                    filtre |= Q(id__istartswith=fin)
            qs = qs.filter(filtre)
        if (statut := params.get('statut')) in dict(ReservationModel.STATUS_CHOICES):
            qs = qs.filter(status=statut)
        # Stays that overlap the requested period
        if debut := parse_date(params.get('debut', '') or ''):
            qs = qs.filter(check_out__gt=debut)
        if fin := parse_date(params.get('fin', '') or ''):
            qs = qs.filter(check_in__lt=fin)
        return _paginer(request, qs, _reservations_json, en_lot=True)


class ReservationAnnulerView(VueAdmin):
    def post(self, request, pk):
        motif, erreur = _motif(request.data.get('motif'))
        if erreur:
            return erreur
        reservation = _reservations().filter(pk=pk).first()
        if not reservation:
            return _introuvable('Réservation')
        try:
            # Cancellation by Kwa-Ba: the traveller is fully refunded if they paid (even for a stay already started)
            rembourse = paiements.annuler(reservation, par='plateforme')
        except paiements.PaiementErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        journaliser('reservation_annulee', request, utilisateur=request.user, reservation_id=str(reservation.pk),
                    reference=reservation.reference, voyageur=reservation.guest.email, rembourse=rembourse, motif=motif)
        return Response(_reservation(_reservations().get(pk=reservation.pk)))


# --- 5. Avis ----------------------------------------------------------------------------------------

def _avis(liste) -> list[dict]:
    annonces = hebergements.resumes({a.hebergement_id for a in liste})
    return [{
        'id': str(a.id), 'note': a.note, 'commentaire': a.commentaire,
        'auteur': {'id': str(a.auteur_id), 'nom': _nom(a.auteur), 'email': a.auteur.email},
        'hebergement': {'id': str(a.hebergement_id), 'name': annonces[a.hebergement_id]['name'] if a.hebergement_id in annonces else ''},
        'reponse_hote': a.reponse_hote, 'created_at': a.created_at,
    } for a in liste]


class AvisListView(VueAdmin):
    def get(self, request):
        qs = AvisModel.objects.select_related('auteur').order_by('-created_at')
        params = request.query_params
        if q := params.get('q', '').strip():
            qs = qs.filter(Q(commentaire__icontains=q) | Q(hebergement_id__in=hebergements.ids_par_nom(q))
                           | Q(auteur__email__icontains=q))
        if (note := _entier(params.get('note'), 0, minimum=0)) in range(1, 6):
            qs = qs.filter(note=note)
        return _paginer(request, qs, _avis, en_lot=True)


class AvisDetailView(VueAdmin):
    def delete(self, request, pk):
        motif, erreur = _motif(request.query_params.get('motif'))
        if erreur:
            return erreur
        avis = AvisModel.objects.select_related('auteur').filter(pk=pk).first()
        if not avis:
            return _introuvable('Avis')
        annonce = hebergements.resumes([avis.hebergement_id]).get(avis.hebergement_id)
        trace = {'avis_id': str(avis.pk), 'annonce': annonce['name'] if annonce else '', 'auteur': avis.auteur.email,
                 'note': avis.note, 'motif': motif}
        avis.delete()  # the post_delete signal of the avis app computes the listing's rating again
        journaliser('avis_supprime', request, utilisateur=request.user, **trace)
        return Response(status=status.HTTP_204_NO_CONTENT)
