"""Back-office: Kwa-Ba's rates (AN-B1) and the money of a period (AN-B2)."""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.response import Response

from apps.activity import api as activity
from apps.securite.backoffice import VueAdmin

from . import finances, tarifs
from .models import FraisMenageModel, ReglagesTarifsModel

# Highest rate the team can set, in %: a typing mistake (60 instead of 6) cannot go through
TAUX_MAX = Decimal('30')
MENAGE_MAX = 100_000


def _pourcent(valeur: Decimal) -> float:
    return float((valeur * 100).quantize(Decimal('0.01')))


def _tarifs_json() -> dict:
    taux = ReglagesTarifsModel.actuels()
    return {
        # In %: 6 means 6 %
        'taux': {champ: _pourcent(getattr(taux, champ)) for champ in ReglagesTarifsModel.TAUX},
        'frais_menage': tarifs.grille_menage(),
        'mis_a_jour_le': taux.mis_a_jour_le,
    }


class TarifsView(VueAdmin):
    """GET: the rates in force. PUT {taux: {frais_voyageur: 6, …}, frais_menage: {studio: 5000, …}}: changes them,
    for the bookings made afterwards (the amounts of a booking are frozen). Every change goes to the audit log."""

    def get(self, request):
        return Response(_tarifs_json())

    def put(self, request):
        avant = _tarifs_json()
        nouveaux_taux, erreurs = {}, {}
        for champ, valeur in (request.data.get('taux') or {}).items():
            if champ not in ReglagesTarifsModel.TAUX:
                continue
            try:
                pourcent = Decimal(str(valeur)).quantize(Decimal('0.01'))
            except (InvalidOperation, ValueError):
                erreurs[champ] = ["Nombre attendu."]
                continue
            if not Decimal('0') <= pourcent <= TAUX_MAX:
                erreurs[champ] = [f"Entre 0 et {TAUX_MAX} %."]
                continue
            nouveaux_taux[champ] = pourcent / 100
        menage = {}
        types = set(tarifs.GRILLE_MENAGE)
        for code, montant in (request.data.get('frais_menage') or {}).items():
            if code not in types:
                continue
            if not isinstance(montant, int) or isinstance(montant, bool) or not 0 <= montant <= MENAGE_MAX:
                erreurs[f'frais_menage.{code}'] = [f"Montant entier entre 0 et {MENAGE_MAX:,} F CFA.".replace(',', ' ')]
                continue
            menage[code] = montant
        if erreurs:
            return Response(erreurs, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            taux = ReglagesTarifsModel.objects.select_for_update().order_by('pk').first() or ReglagesTarifsModel()
            for champ, valeur in nouveaux_taux.items():
                setattr(taux, champ, valeur)
            if taux.frais_reduits > taux.frais_voyageur:
                return Response({'frais_reduits': ["Les frais réduits ne peuvent pas dépasser les frais de service."]},
                                status=status.HTTP_400_BAD_REQUEST)
            taux.mis_a_jour_par_id = request.user.pk
            taux.save()
            for code, montant in menage.items():
                FraisMenageModel.objects.update_or_create(type_logement=code, defaults={'montant': montant})
        apres = _tarifs_json()
        activity.record('tarifs_modifies', request, actor=request.user,
                        avant={**avant['taux'], **{f'menage_{k}': v for k, v in avant['frais_menage'].items()}},
                        apres={**apres['taux'], **{f'menage_{k}': v for k, v in apres['frais_menage'].items()}})
        return Response(apres)


# Longest period of a report: a year, enough for the accounts, never a query on the whole history by mistake
PERIODE_MAX_JOURS = 366


def _periode(request):
    """?debut=&fin= (YYYY-MM-DD, both included); this month so far by default."""
    aujourd_hui = timezone.localdate()
    debut = parse_date(request.query_params.get('debut') or '') or aujourd_hui.replace(day=1)
    fin = parse_date(request.query_params.get('fin') or '') or aujourd_hui
    if fin < debut:
        return None, None, Response({'detail': 'La fin doit être après le début.'}, status=status.HTTP_400_BAD_REQUEST)
    if (fin - debut) > timedelta(days=PERIODE_MAX_JOURS):
        return None, None, Response({'detail': 'Un an au plus.'}, status=status.HTTP_400_BAD_REQUEST)
    return debut, fin, None


class FinancesView(VueAdmin):
    """GET ?debut=&fin=: collected, refunded, paid to the partners, due to them, Kwa-Ba's revenue, day by day."""

    def get(self, request):
        debut, fin, erreur = _periode(request)
        return erreur or Response(finances.rapport(debut, fin))


class FinancesExportView(VueAdmin):
    """GET ?debut=&fin=: the report as a CSV file (every movement) or a PDF (summary and reconciliation)."""

    def get(self, request, format_export):
        if format_export not in ('csv', 'pdf'):
            return Response({'detail': 'Format inconnu : csv ou pdf.'}, status=status.HTTP_404_NOT_FOUND)
        debut, fin, erreur = _periode(request)
        if erreur:
            return erreur
        donnees = finances.rapport(debut, fin)
        nom = f"kwaba-finances-{debut:%Y%m%d}-{fin:%Y%m%d}"
        if format_export == 'csv':
            reponse = HttpResponse(finances.en_csv(donnees), content_type='text/csv; charset=utf-8')
        else:
            reponse = HttpResponse(finances.en_pdf(donnees), content_type='application/pdf')
        reponse['Content-Disposition'] = f'attachment; filename="{nom}.{format_export}"'
        reponse['Cache-Control'] = 'no-store'
        activity.record('finances_exportees', request, actor=request.user, format=format_export,
                        debut=str(debut), fin=str(fin))
        return reponse
