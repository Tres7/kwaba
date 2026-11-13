"""Use cases of the finance module: write movements in the ledger, correct them, read the parameters and the
reports."""
import uuid
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Iterable

from apps.finance.application.ports import Alertes, Clock, GrandLivre, Journal, Parametres, Restitutions, TransactionManager
from apps.finance.domain.entities import PERIODE_VERROUILLEE, Ecriture, Ecrivain, Ligne
from apps.finance.domain.exceptions import MouvementRefuse, RestitutionRefusee
from apps.finance.domain.rules import ecarts_des_modules_ouverts, inverse, preparer, premier_du_mois


class GrandLivreService:
    def __init__(self, *, grand_livre: GrandLivre, parametres: Parametres, alertes: Alertes, journal: Journal,
                 tx: TransactionManager, clock: Clock):
        self.grand_livre = grand_livre
        self.parametres = parametres
        self.alertes = alertes
        self.journal = journal
        self.tx = tx
        self.clock = clock

    def enregistrer(self, lignes: Iterable[Ligne], *, origine: str, par_id: uuid.UUID | None = None) -> list[int]:
        """Writes the lines, all or none, in the caller's transaction (FIN-01.6). Returns the ids of the new lines: a
        line of an external event already written is skipped (FIN-01.7). A refusal raises MouvementRefuse and alerts
        the finance team (FIN-01.4)."""
        lignes = list(lignes)
        origine = (origine or '').strip()
        try:
            if not origine:
                raise MouvementRefuse("L'origine du mouvement est obligatoire (paiement, versement, remboursement…).")
            if not lignes:
                return []
            maintenant = self.clock.now()
            ref = self.grand_livre.referentiels(lignes)
            ecritures = [preparer(ligne, ref, origine=origine, par_id=par_id, maintenant=maintenant)
                         for ligne in lignes]
            crees = []
            with self.tx.atomic():
                for ecriture in ecritures:
                    self._verifier_periode(ecriture)
                    pk = self.grand_livre.ecrire(ecriture)
                    if pk is None:
                        self._verifier_doublon(ecriture)
                    else:
                        crees.append(pk)
            return crees
        except MouvementRefuse as refus:
            self.alertes.mouvement_refuse(origine or 'inconnue', str(refus))
            raise

    def contre_passer(self, mouvement_id: int, *, motif: str, origine: str = 'correction',
                      par_id: uuid.UUID | None = None) -> int:
        """Cancels a line by an inverse line (FIN-01.3); both stay visible. A line is corrected once at most. The
        correction goes to the audit log (FIN-13.3)."""
        mouvement = self.grand_livre.mouvement(mouvement_id)
        if mouvement is None:
            raise MouvementRefuse(f'Ligne {mouvement_id} inconnue : rien à corriger.')
        ecriture = inverse(mouvement, motif=motif, origine=origine, par_id=par_id, maintenant=self.clock.now())
        with self.tx.atomic():
            # Two corrections of the same line at the same time: the second waits, then sees the first
            self.grand_livre.verrouiller(f'finance:correction:{mouvement_id}')
            if self.grand_livre.est_corrige(mouvement_id):
                raise MouvementRefuse(f'La ligne {mouvement_id} a déjà été corrigée.')
            self._verifier_periode(ecriture)
            pk = self.grand_livre.ecrire(ecriture)
            self.journal.correction(par_id, mouvement_id, pk, ecriture.ligne.motif)
        return pk

    def rectifier(self, nature: str, nouveau_montant: int, *, motif: str, origine: str, objet: dict,
                  par_id: uuid.UUID | None = None) -> list[int]:
        """Brings the amount of a nature for an object (booking, transfer, rental) to `nouveau_montant`: its lines in
        force are cancelled by inverse lines, and a new line carries the right amount (none if 0). Every line stays
        visible (FIN-01.3). For example, service fees lowered from 6 to 3 % after the payment."""
        if type(nouveau_montant) is not int or nouveau_montant < 0:
            raise MouvementRefuse('Le nouveau montant doit être un nombre entier de francs CFA, positif ou nul.')
        with self.tx.atomic():
            lignes = self.grand_livre.lignes_en_vigueur(nature, **objet)
            if not lignes:
                raise MouvementRefuse(f'Aucune ligne {nature} en vigueur pour cet objet : rien à rectifier.')
            ids = [self.contre_passer(m.id, motif=motif, origine=origine, par_id=par_id) for m in lignes]
            if nouveau_montant:
                nouvelle = replace(lignes[0].ligne, montant=nouveau_montant, motif=motif, date_evenement=None,
                                   externe_reference=None)
                ids += self.enregistrer([nouvelle], origine=origine, par_id=par_id)
            return ids

    def a_des_lignes(self, **filtres) -> bool:
        return self.grand_livre.a_des_lignes(**filtres)

    def parametre(self, cle: str) -> Decimal:
        """Value in force of a steered parameter (FIN-16). An unknown or inactive key is an error: an offer not open
        yet has no value to read."""
        trouve = self.parametres.lire(cle)
        if trouve is None:
            raise ValueError(f'Paramètre « {cle} » inconnu.')
        valeur, actif = trouve
        if not actif:
            raise ValueError(f'Paramètre « {cle} » inactif : son offre n\'est pas ouverte.')
        return valeur

    def _verifier_periode(self, ecriture: Ecriture) -> None:
        if self.grand_livre.etat_periode(ecriture.mois) == PERIODE_VERROUILLEE:
            raise MouvementRefuse(f'La période {ecriture.mois:%m/%Y} est verrouillée : écriture refusée.')

    def _verifier_doublon(self, ecriture: Ecriture) -> None:
        """The event was already written: a delivery repeated with another amount is an anomaly to look at (the
        reconciliation with the provider will show it too)."""
        deja = self.grand_livre.deja_ecrite(ecriture)
        if deja is not None and deja.ligne.montant != ecriture.ligne.montant:
            self.alertes.evenement_rejoue(deja.id, ecriture.ligne.nature)


class RestitutionService:
    """Reports of the ledger (FIN-04, FIN-07, FIN-17). None computes again from the bookings."""

    def __init__(self, *, restitutions: Restitutions, ecrivains: dict[str, Ecrivain]):
        self.restitutions = restitutions
        self.ecrivains = ecrivains

    def controle_invariants(self) -> list[dict]:
        """The invariants of the database, and I14: no open module writes to an inactive offer or nature."""
        return [*self.restitutions.controle_invariants(),
                {'invariant': 'I14', 'libelle': 'Modules ouverts : offres et natures actives',
                 'anomalies': len(self.ecarts_des_modules_ouverts())}]

    def ecarts_des_modules_ouverts(self) -> list[str]:
        offres, natures = self.restitutions.codes_actifs()
        return ecarts_des_modules_ouverts(self.ecrivains.values(), offres, natures)

    def peut_on_cloturer(self, mois: date) -> list[dict]:
        return self.restitutions.peut_on_cloturer(premier_du_mois(mois))

    def synthese(self, debut: date, fin: date, axe1: str = 'mois', axe2: str | None = None, familles=None,
                 offres=None) -> list[dict]:
        return self.restitutions.synthese(debut, fin, axe1, axe2, list(familles) if familles else None,
                                          list(offres) if offres else None)

    def rapport(self, code: str, debut: date, fin: date) -> list[dict]:
        defini = self.restitutions.rapport_defini(code)
        if defini is None:
            raise RestitutionRefusee(f'Rapport « {code} » inconnu ou inactif.')
        return self.synthese(debut, fin, defini['axe1'], defini['axe2'], defini['familles'], defini['offres'])

    def du_aux_partenaires(self) -> list[dict]:
        return self.restitutions.du_aux_partenaires()

    def derniers_mouvements(self, limite: int = 50) -> list[dict]:
        return self.restitutions.derniers_mouvements(max(1, min(limite, 500)))

    def cautions_detenues(self) -> list[dict]:
        return self.restitutions.cautions_detenues()

    def soldes_comptes_argent(self) -> dict[str, int]:
        return self.restitutions.soldes_comptes_argent()

    def balance_generale(self, mois: date | None = None) -> list[dict]:
        return self.restitutions.balance_generale(premier_du_mois(mois) if mois else None)

    def controle_equilibre(self) -> list[dict]:
        return self.restitutions.controle_equilibre()

    def marge_par_offre(self, mois: date) -> list[dict]:
        return self.restitutions.marge_par_offre(premier_du_mois(mois))

    def ecritures(self, mois: date) -> list[dict]:
        return self.restitutions.ecritures(premier_du_mois(mois))
