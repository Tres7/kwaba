"""Money of a period for the back-office (AN-B2): what was collected, refunded, paid to the partners, what is still due
to them, Kwa-Ba's revenue, and a day-by-day reconciliation. Exported as CSV and PDF.

Each paid product (stays, transfers, rentals, donations) gives its revenue and its partner payouts through the registry
(registre.ProduitPaye): paiements never imports them.
"""
import csv
import io
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.users import api as users

from .models import PaiementModel, RemboursementModel, VersementModel
from .registre import PRODUITS

PRODUITS_LIBELLES = {'reservation': 'Séjour', 'transfert': 'Transfert', 'location': 'Location', 'don': 'Don'}
PRESTATAIRES = {'fedapay': 'FedaPay', 'paypal': 'PayPal'}
STATUTS = {'planifie': 'Planifié', 'en_cours': 'En cours', 'envoye': 'Envoyé', 'echoue': 'Échoué',
           'a_envoyer': 'À envoyer', 'attente_numero': 'Numéro attendu'}
# Payouts still to be sent: due to the partners
A_VERSER = ('planifie', 'en_cours', 'echoue')


def _bornes(debut: date, fin: date) -> tuple[datetime, datetime]:
    """[first day 00:00, day after the last one 00:00), local time (Lomé)."""
    return (timezone.make_aware(datetime.combine(debut, time.min)),
            timezone.make_aware(datetime.combine(fin + timedelta(days=1), time.min)))


def _jour(valeur) -> date | None:
    if valeur is None:
        return None
    return timezone.localtime(valeur).date() if isinstance(valeur, datetime) else valeur


def _versements_hotes(a, b) -> list[dict]:
    qs = list(VersementModel.objects.filter(Q(envoye_le__gte=a, envoye_le__lt=b) | Q(statut__in=A_VERSER)))
    hotes = users.comptes({v.hote_id for v in qs})
    nom = lambda u: (f"{u.first_name} {u.last_name}".strip() or u.email) if u else ''  # noqa: E731
    return [{
        'categorie': 'Hôte', 'beneficiaire': nom(hotes.get(v.hote_id)), 'objet': f"RES-{str(v.reservation_id)[:8].upper()}",
        'montant': v.montant, 'commission': v.commission, 'statut': v.statut, 'date_prevue': v.date_prevue,
        'envoye_le': v.envoye_le,
    } for v in qs]


def rapport(debut: date, fin: date) -> dict:
    """Everything the Finances page shows for the days [debut, fin]."""
    a, b = _bornes(debut, fin)

    encaissements = []
    payes_par_type = defaultdict(list)
    for p in PaiementModel.objects.filter(statut='reussi', cree_le__gte=a, cree_le__lt=b).order_by('cree_le'):
        description = p.description or {}
        encaissements.append({
            'date': p.cree_le, 'produit': p.type_objet, 'reference': description.get('reference', ''),
            'libelle': description.get('libelle', ''), 'prestataire': p.prestataire, 'mode': p.mode, 'montant': p.montant,
        })
        payes_par_type[p.type_objet].append(p.objet_id)

    revenu = 0
    for type_objet, ids in payes_par_type.items():
        produit = PRODUITS.get(type_objet)
        if produit and produit.revenu:
            revenu += sum(produit.revenu(ids).values())

    remboursements = [{
        'date': r.envoye_le or r.cree_le, 'produit': next((t for t in PRODUITS_LIBELLES if getattr(r, f'{t}_id', None)), ''),
        'reference': r.paiement.reference if r.paiement_id else '', 'motif': r.motif, 'montant': r.montant, 'statut': r.statut,
    } for r in RemboursementModel.objects.select_related('paiement').filter(
        Q(envoye_le__gte=a, envoye_le__lt=b) | (Q(cree_le__gte=a, cree_le__lt=b) & ~Q(statut='envoye'))).order_by('cree_le')]

    versements = _versements_hotes(a, b)
    for produit in PRODUITS.values():
        if produit.versements_periode:
            versements += produit.versements_periode(a, b)
    versements.sort(key=lambda v: (_jour(v['envoye_le'] or v['date_prevue']) or debut))

    envoyes = [v for v in versements if v['statut'] == 'envoye']
    jours = {}
    for i in range((fin - debut).days + 1):
        jour = debut + timedelta(days=i)
        jours[jour] = {'date': jour, 'nb_paiements': 0, 'encaisse': 0, 'rembourse': 0, 'verse': 0}
    for e in encaissements:
        ligne = jours.get(_jour(e['date']))
        if ligne:
            ligne['nb_paiements'] += 1
            ligne['encaisse'] += e['montant']
    for r in remboursements:
        if r['statut'] == 'envoye' and (ligne := jours.get(_jour(r['date']))):
            ligne['rembourse'] += r['montant']
    for v in envoyes:
        if ligne := jours.get(_jour(v['envoye_le'])):
            ligne['verse'] += v['montant']
    for ligne in jours.values():
        ligne['solde'] = ligne['encaisse'] - ligne['rembourse'] - ligne['verse']

    par_produit = defaultdict(int)
    par_prestataire = defaultdict(int)
    for e in encaissements:
        par_produit[e['produit']] += e['montant']
        par_prestataire[e['prestataire']] += e['montant']
    return {
        'debut': debut, 'fin': fin,
        'totaux': {
            'encaisse': sum(e['montant'] for e in encaissements),
            'nb_paiements': len(encaissements),
            'rembourse': sum(r['montant'] for r in remboursements if r['statut'] == 'envoye'),
            'rembourse_en_attente': sum(r['montant'] for r in remboursements if r['statut'] != 'envoye'),
            'verse': sum(v['montant'] for v in envoyes),
            'du_partenaires': sum(v['montant'] for v in versements if v['statut'] in A_VERSER),
            'revenu_kwaba': revenu,
        },
        'par_produit': dict(par_produit),
        'par_prestataire': dict(par_prestataire),
        'jours': list(jours.values()),
        'encaissements': encaissements,
        'remboursements': remboursements,
        'versements': versements,
    }


def _fcfa(montant: int) -> str:
    return f"{int(montant):,}".replace(',', ' ') + ' F'


def _date(valeur) -> str:
    jour = _jour(valeur)
    return jour.strftime('%d/%m/%Y') if jour else ''


def en_csv(donnees: dict) -> bytes:
    """Every money movement of the period, one per line, for a spreadsheet (separator ;, UTF-8 for Excel)."""
    tampon = io.StringIO()
    ecrit = csv.writer(tampon, delimiter=';')
    ecrit.writerow(['Date', 'Mouvement', 'Produit ou bénéficiaire', 'Référence', 'Détail', 'Moyen', 'Montant (F CFA)',
                    'Commission (F CFA)', 'Statut'])
    for e in donnees['encaissements']:
        ecrit.writerow([_date(e['date']), 'Encaissement', PRODUITS_LIBELLES.get(e['produit'], e['produit']), e['reference'],
                        e['libelle'], ' '.join(x for x in (PRESTATAIRES.get(e['prestataire'], e['prestataire']), e['mode']) if x),
                        e['montant'], '', 'Réussi'])
    for r in donnees['remboursements']:
        ecrit.writerow([_date(r['date']), 'Remboursement', PRODUITS_LIBELLES.get(r['produit'], r['produit']), r['reference'],
                        r['motif'], '', -r['montant'], '', STATUTS.get(r['statut'], r['statut'])])
    for v in donnees['versements']:
        ecrit.writerow([_date(v['envoye_le'] or v['date_prevue']), f"Versement · {v['categorie']}", v['beneficiaire'], v['objet'],
                        '' if v['envoye_le'] else 'à verser', '', -v['montant'], v['commission'], STATUTS.get(v['statut'], v['statut'])])
    return ('﻿' + tampon.getvalue()).encode('utf-8')


def en_pdf(donnees: dict) -> bytes:
    """Summary of the period and the day-by-day reconciliation, with the Kwa-Ba letterhead."""
    from apps.documents.api import Document  # local import: documents registers the paid products' documents

    t = donnees['totaux']
    periode = f"du {_date(donnees['debut'])} au {_date(donnees['fin'])}"
    doc = Document('Rapport financier', f"{donnees['debut']:%Y%m%d}-{donnees['fin']:%Y%m%d}", sous_titre=periode)
    doc.bloc('Synthèse', [
        ('Encaissé', f"{_fcfa(t['encaisse'])} ({t['nb_paiements']} paiement{'s' if t['nb_paiements'] > 1 else ''})"),
        ('Remboursé', _fcfa(t['rembourse']) + (f" ; {_fcfa(t['rembourse_en_attente'])} en attente" if t['rembourse_en_attente'] else '')),
        ('Versé aux partenaires', _fcfa(t['verse'])),
        ('Dû aux partenaires', _fcfa(t['du_partenaires'])),
        ('Revenu Kwa-Ba', f"{_fcfa(t['revenu_kwaba'])} (frais de service et commissions des paiements encaissés)"),
    ])
    if donnees['par_produit']:
        doc.tableau('Encaissé par produit', ['Produit', 'Montant'],
                    [[PRODUITS_LIBELLES.get(k, k), _fcfa(v)] for k, v in donnees['par_produit'].items()], [110, 60])
    doc.tableau('Rapprochement jour par jour', ['Jour', 'Paiements', 'Encaissé', 'Remboursé', 'Versé', 'Solde'],
                [[_date(j['date']), str(j['nb_paiements']), _fcfa(j['encaisse']), _fcfa(j['rembourse']), _fcfa(j['verse']),
                  _fcfa(j['solde'])] for j in donnees['jours'] if j['nb_paiements'] or j['rembourse'] or j['verse']]
                or [['Aucun mouvement', '', '', '', '', '']], [30, 22, 30, 30, 28, 30])
    a_verser = [v for v in donnees['versements'] if v['statut'] in A_VERSER]
    if a_verser:
        doc.tableau('Dû aux partenaires', ['Bénéficiaire', 'Objet', 'Prévu le', 'Montant'],
                    [[f"{v['beneficiaire']} ({v['categorie']})", v['objet'], _date(v['date_prevue']), _fcfa(v['montant'])]
                     for v in a_verser], [70, 40, 28, 32])
    doc.paragraphe(f"Document établi le {_date(timezone.now())}. Le détail de chaque mouvement est dans l'export CSV.", 'petit')
    return doc.en_pdf()
