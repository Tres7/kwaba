"""Django adapters of the ledger: reference tables, accounting months, lines, parameters."""
from contextlib import AbstractContextManager
from decimal import Decimal

from django.db import DatabaseError, IntegrityError, connection, transaction

from apps.finance.application.ports import GrandLivre, Parametres, TransactionManager
from apps.finance.domain.entities import Ecriture, Ligne, Mouvement, Nature, Referentiels
from apps.finance.domain.exceptions import MouvementRefuse
from apps.finance.infrastructure.persistence.models import (CLE_IDEMPOTENCE, CORRECTION_UNIQUE, CompteArgentModel,
                                                            MouvementModel, MoyenPaiementModel, NatureModel,
                                                            OffreModel, ParametreModel, PeriodeModel, TiersTypeModel)

# SQLSTATE of RAISE EXCEPTION: a refusal of the database guards (migration 0003)
REFUS_BASE = 'P0001'


def diagnostic(erreur: DatabaseError):
    """Diagnostic of the PostgreSQL error (psycopg 2 and 3 both give .diag with sqlstate, constraint_name and
    message_primary)."""
    return getattr(erreur.__cause__, 'diag', None)


class DjangoTransactionManager(TransactionManager):
    def atomic(self) -> AbstractContextManager:
        return transaction.atomic()


def _actifs(modele, codes, champ: str = 'actif') -> dict[str, bool]:
    codes = {code for code in codes if code}
    return dict(modele.objects.filter(code__in=codes).values_list('code', champ)) if codes else {}


def _texte_id(valeur) -> str | None:
    return None if valeur is None else str(valeur)


def _mouvement(m: MouvementModel) -> Mouvement:
    return Mouvement(
        id=m.pk, mois=m.periode_id, origine=m.origine, annule_mouvement_id=m.annule_mouvement_id,
        ligne=Ligne(
            nature=m.nature_id, offre=m.offre_id, montant=m.montant, sens=m.sens, compte_argent=m.compte_argent_id,
            tiers_type=m.tiers_type_id, tiers_id=m.tiers_id, moyen_paiement=m.moyen_paiement_id,
            piece_reference=m.piece_reference, externe_reference=m.externe_reference, reservation_id=m.reservation_id,
            ligne_reservation_id=m.ligne_reservation_id, prestation_type=m.prestation_type,
            transfert_id=m.transfert_id, location_id=m.location_id, date_evenement=m.date_evenement, motif=m.motif,
            devise=m.devise, metadonnees=m.metadonnees,
        ),
    )


def _ligne_en_base(ecriture: Ecriture) -> MouvementModel:
    ligne = ecriture.ligne
    return MouvementModel(
        date_evenement=ecriture.date_evenement, periode_id=ecriture.mois, montant=ligne.montant, devise=ligne.devise,
        sens=ligne.sens, nature_id=ligne.nature, offre_id=ligne.offre, tiers_type_id=ligne.tiers_type,
        tiers_id=_texte_id(ligne.tiers_id), moyen_paiement_id=ligne.moyen_paiement, compte_argent_id=ligne.compte_argent,
        piece_reference=ligne.piece_reference, reservation_id=ligne.reservation_id,
        ligne_reservation_id=ligne.ligne_reservation_id, prestation_type=ligne.prestation_type,
        transfert_id=ligne.transfert_id, location_id=ligne.location_id, externe_reference=ligne.externe_reference,
        annule_mouvement_id=ecriture.annule_mouvement_id, motif=ligne.motif, cree_par_id=ecriture.par_id,
        origine=ecriture.origine, metadonnees=ligne.metadonnees,
    )


class DjangoGrandLivre(GrandLivre):
    def referentiels(self, lignes: list[Ligne]) -> Referentiels:
        natures = NatureModel.objects.filter(code__in={x.nature for x in lignes if x.nature})
        return Referentiels(
            natures={n.code: Nature(code=n.code, famille=n.famille_id, sens_attendu=n.sens_attendu, actif=n.actif)
                     for n in natures},
            offres=_actifs(OffreModel, {x.offre for x in lignes}, champ='active'),
            comptes_argent=_actifs(CompteArgentModel, {x.compte_argent for x in lignes}),
            tiers_types=_actifs(TiersTypeModel, {x.tiers_type for x in lignes}),
            moyens_paiement=_actifs(MoyenPaiementModel, {x.moyen_paiement for x in lignes}),
        )

    def etat_periode(self, mois) -> str:
        periode, _ = PeriodeModel.objects.get_or_create(mois=mois)
        return periode.etat

    def ecrire(self, ecriture: Ecriture) -> int | None:
        objet = _ligne_en_base(ecriture)
        try:
            # A savepoint: a refused line leaves the caller's transaction usable
            with transaction.atomic():
                objet.save(force_insert=True)
        except IntegrityError as erreur:
            contrainte = getattr(diagnostic(erreur), 'constraint_name', None)
            if contrainte == CLE_IDEMPOTENCE:
                return None
            if contrainte == CORRECTION_UNIQUE:
                # No row lock is taken to prevent it: the application role may not lock the ledger (no UPDATE
                # right), the unique index settles two simultaneous corrections
                raise MouvementRefuse(f'La ligne {ecriture.annule_mouvement_id} a déjà été corrigée.') from erreur
            raise
        except DatabaseError as erreur:
            diag = diagnostic(erreur)
            if getattr(diag, 'sqlstate', None) != REFUS_BASE:
                raise
            raise MouvementRefuse(getattr(diag, 'message_primary', None) or str(erreur)) from erreur
        return objet.pk

    def deja_ecrite(self, ecriture: Ecriture) -> Mouvement | None:
        ligne = ecriture.ligne
        trouve = MouvementModel.objects.filter(
            externe_reference=ligne.externe_reference, nature_id=ligne.nature, sens=ligne.sens,
            compte_argent_id=ligne.compte_argent, tiers_id=_texte_id(ligne.tiers_id),
            ligne_reservation_id=ligne.ligne_reservation_id, annule_mouvement__isnull=True,
        ).first()
        return _mouvement(trouve) if trouve else None

    def mouvement(self, mouvement_id: int) -> Mouvement | None:
        trouve = MouvementModel.objects.filter(pk=mouvement_id).first()
        return _mouvement(trouve) if trouve else None

    def est_corrige(self, mouvement_id: int) -> bool:
        return MouvementModel.objects.filter(annule_mouvement_id=mouvement_id).exists()

    def a_des_lignes(self, *, externe_reference=None, reservation_id=None, transfert_id=None,
                     location_id=None) -> bool:
        filtres = {nom: valeur for nom, valeur in (('externe_reference', externe_reference),
                                                    ('reservation_id', reservation_id), ('transfert_id', transfert_id),
                                                    ('location_id', location_id)) if valeur is not None}
        return bool(filtres) and MouvementModel.objects.filter(**filtres).exists()

    def lignes_en_vigueur(self, nature: str, *, reservation_id=None, transfert_id=None,
                          location_id=None) -> list[Mouvement]:
        objet = {nom: valeur for nom, valeur in (('reservation_id', reservation_id), ('transfert_id', transfert_id),
                                                  ('location_id', location_id)) if valeur is not None}
        if not objet:
            return []
        lignes = (MouvementModel.objects.filter(nature_id=nature, annule_mouvement__isnull=True, **objet)
                  .exclude(corrections__isnull=False).order_by('pk'))
        return [_mouvement(m) for m in lignes]

    def verrouiller(self, cle: str) -> None:
        # Advisory lock of the transaction: needs no right on any table, released at its end
        with connection.cursor() as curseur:
            curseur.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))', [cle])


class DjangoParametres(Parametres):
    def lire(self, cle: str) -> tuple[Decimal, bool] | None:
        return ParametreModel.objects.filter(cle=cle).values_list('valeur', 'actif').first()
