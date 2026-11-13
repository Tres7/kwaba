"""Back-office, section Finances: the ledger at a glance (control of the invariants, the three balances that never
mix, sums owed by partner, latest lines). Read only."""
import uuid

from django.utils import timezone
from rest_framework.response import Response

from apps.finance import api as finance
from apps.securite.backoffice import VueAdmin
from apps.users import api as users


def _uuid(valeur):
    try:
        return uuid.UUID(str(valeur))
    except (TypeError, ValueError):
        return None


def _comptes(tiers_ids) -> dict[str, dict]:
    """Name and email of the third parties that are accounts (hosts, travellers), in one read: two hosts may have
    the same name. Others (drivers, rental partners) keep their id."""
    ids = {u for u in (_uuid(t) for t in tiers_ids) if u}
    return {str(pk): {'nom': f"{c.first_name} {c.last_name}".strip() or c.email, 'email': c.email}
            for pk, c in users.comptes(ids).items()}


class GrandLivreView(VueAdmin):
    def get(self, request):
        aujourdhui = timezone.localdate()
        du = finance.du_aux_partenaires()
        mouvements = finance.derniers_mouvements(50)
        comptes = _comptes([*(d['tiers_id'] for d in du), *(m['tiers_id'] for m in mouvements)])
        inconnu = {'nom': '', 'email': ''}
        revenu = sum(r['montant'] for r in finance.synthese(aujourdhui.replace(day=1), aujourdhui, 'famille',
                                                           familles=['R']))
        return Response({
            'invariants': finance.controle_invariants(),
            'soldes': {
                'revenu_du_mois': revenu,
                'du_partenaires': sum(d['solde_du'] for d in du if d['tiers_type'] != 'voyageur'),
                'du_voyageurs': sum(d['solde_du'] for d in du if d['tiers_type'] == 'voyageur'),
                'cautions_detenues': sum(c['solde_detenu'] for c in finance.cautions_detenues()),
                'comptes': finance.soldes_comptes_argent(),
            },
            'du_aux_partenaires': [{**d, **comptes.get(d['tiers_id'], inconnu)} for d in du],
            'mouvements': [{**m, **comptes.get(m['tiers_id'] or '', inconnu)} for m in mouvements],
        })
