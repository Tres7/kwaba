"""Back-office: bookings (list, cancellation by Kwa-Ba)."""
from django.db.models import Q
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.response import Response

from apps.hebergements import api as hebergements
from apps.paiements import api as paiements
from apps.securite.audit import journaliser
from apps.users import api as users
from apps.securite.backoffice import VueAdmin, introuvable as _introuvable, motif as _motif, nom as _nom, paginer as _paginer

from . import paiement
from .models import ReservationModel


def _reservations_json(liste) -> list[dict]:
    annonces = hebergements.resumes({r.hebergement_id for r in liste})
    personnes = users.comptes({a['host_id'] for a in annonces.values()} | {r.guest_id for r in liste})
    resultats = []
    for r in liste:
        h = annonces.get(r.hebergement_id, {})
        hote, voyageur = personnes.get(h.get('host_id')), personnes.get(r.guest_id)
        resultats.append({
            'id': str(r.id), 'reference': r.reference,
            'hebergement': {'id': str(r.hebergement_id), 'name': h.get('name', ''), 'city': h.get('city', '')},
            'voyageur': {'id': str(r.guest_id), 'nom': _nom(voyageur) if voyageur else '', 'email': voyageur.email if voyageur else ''},
            'hote': {'id': str(h['host_id']) if h else '', 'nom': _nom(hote) if hote else ''},
            'check_in': r.check_in, 'check_out': r.check_out, 'nights': r.nights, 'guests_count': r.guests_count,
            'total_price': int(r.total_price), 'status': r.status, 'payment_method': r.payment_method,
            'created_at': r.created_at,
        })
    return resultats


def _reservation(r) -> dict:
    return _reservations_json([r])[0]


def _reservations():
    return ReservationModel.objects.order_by('-created_at')


class ReservationListView(VueAdmin):
    def get(self, request):
        qs = _reservations()
        params = request.query_params
        if q := params.get('q', '').strip():
            filtre = Q(hebergement_id__in=hebergements.ids_par_nom(q)) | Q(guest_id__in=users.ids_par_recherche(q))
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
            rembourse = paiement.annuler(reservation, par='plateforme')
        except paiements.PaiementErreur as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        journaliser('reservation_annulee', request, utilisateur=request.user, reservation_id=str(reservation.pk),
                    reference=reservation.reference, voyageur=reservation.guest.email, rembourse=rembourse, motif=motif)
        return Response(_reservation(_reservations().get(pk=reservation.pk)))


