"""Reads of the reporting views and functions (sql_restitutions.py). Amounts come out as whole FCFA (int)."""
from datetime import date

from django.db import DatabaseError, connection, transaction

from apps.finance.application.ports import Restitutions
from apps.finance.domain.exceptions import RestitutionRefusee
from apps.finance.infrastructure.persistence.models import NatureModel, OffreModel, RapportModel
from apps.finance.infrastructure.persistence.repositories import REFUS_BASE, diagnostic


def _lignes(sql: str, params=()) -> list[dict]:
    # A savepoint: a refusal of the database (unknown axis…) leaves the caller's transaction usable
    with transaction.atomic(), connection.cursor() as curseur:
        curseur.execute(sql, params)
        noms = [colonne.name for colonne in curseur.description]
        return [dict(zip(noms, ligne)) for ligne in curseur.fetchall()]


class SqlRestitutions(Restitutions):
    def controle_invariants(self) -> list[dict]:
        return _lignes('SELECT invariant, libelle, anomalies::bigint AS anomalies FROM finance_controle_invariants')

    def codes_actifs(self) -> tuple[set[str], set[str]]:
        return (set(OffreModel.objects.filter(active=True).values_list('code', flat=True)),
                set(NatureModel.objects.filter(actif=True).values_list('code', flat=True)))

    def peut_on_cloturer(self, mois: date) -> list[dict]:
        return _lignes('SELECT controle, resultat, verdict, que_faire FROM finance_peut_on_cloturer(%s)', [mois])

    def synthese(self, debut, fin, axe1, axe2, familles, offres) -> list[dict]:
        try:
            return _lignes(
                'SELECT axe1, axe2, nb, montant FROM finance_synthese(%s, %s, %s, %s, %s::text[], %s::text[])',
                [debut, fin, axe1, axe2, familles, offres])
        except DatabaseError as erreur:
            diag = diagnostic(erreur)
            if getattr(diag, 'sqlstate', None) != REFUS_BASE:
                raise
            raise RestitutionRefusee(diag.message_primary) from erreur

    def rapport_defini(self, code: str) -> dict | None:
        return RapportModel.objects.filter(code=code, actif=True).values('axe1', 'axe2', 'familles', 'offres').first()

    def du_aux_partenaires(self) -> list[dict]:
        return _lignes('SELECT tiers_type, tiers_id, solde_du::bigint AS solde_du FROM finance_du_aux_partenaires '
                       'ORDER BY tiers_type, tiers_id')

    def cautions_detenues(self) -> list[dict]:
        return _lignes('SELECT reservation_id, location_id, solde_detenu::bigint AS solde_detenu '
                       'FROM finance_cautions_detenues ORDER BY reservation_id, location_id')

    def soldes_comptes_argent(self) -> dict[str, int]:
        return {ligne['compte_argent_code']: ligne['solde_livre'] for ligne in _lignes(
            'SELECT compte_argent_code, solde_livre::bigint AS solde_livre FROM finance_solde_compte_argent')}

    def balance_generale(self, mois: date | None) -> list[dict]:
        sql = ('SELECT mois_comptable, compte_general, nb_lignes::bigint AS nb_lignes, '
               'total_debit::bigint AS total_debit, total_credit::bigint AS total_credit, solde::bigint AS solde '
               'FROM finance_balance_generale')
        return _lignes(sql) if mois is None else _lignes(sql + ' WHERE mois_comptable = %s', [mois])

    def controle_equilibre(self) -> list[dict]:
        return _lignes('SELECT mois_comptable, total_debit::bigint AS total_debit, '
                       'total_credit::bigint AS total_credit, ecart::bigint AS ecart FROM finance_controle_equilibre')

    def marge_par_offre(self, mois: date) -> list[dict]:
        return _lignes('SELECT offre_code, recettes::bigint AS recettes, '
                       'charges_variables::bigint AS charges_variables, marge::bigint AS marge '
                       'FROM finance_marge_par_offre WHERE mois_comptable = %s ORDER BY offre_code', [mois])

    def ecritures(self, mois: date) -> list[dict]:
        return _lignes('SELECT mouvement_id, ligne_ecriture, journal, compte_general, compte_auxiliaire, piece, '
                       'libelle, debit, credit FROM finance_ecriture WHERE mois_comptable = %s '
                       'ORDER BY mouvement_id, ligne_ecriture', [mois])
