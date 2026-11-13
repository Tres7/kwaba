"""Use cases of the ledger with fake adapters: what is written, alerted and logged, without a database."""
import uuid
from contextlib import nullcontext
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from apps.finance.application.ports import Alertes, Clock, GrandLivre, Journal, Parametres, TransactionManager
from apps.finance.application.service import GrandLivreService
from apps.finance.domain.entities import ENTREE, PERIODE_VERROUILLEE, Ligne, Mouvement, Nature, Referentiels
from apps.finance.domain.exceptions import MouvementRefuse

MAINTENANT = datetime(2026, 12, 20, 10, 0, tzinfo=timezone.utc)
HOTE = uuid.uuid4()


class FauxGrandLivre(GrandLivre):
    def __init__(self):
        self.lignes: dict[int, Mouvement] = {}
        self.verrouilles: set[date] = set()
        self.verrous: list[str] = []

    def referentiels(self, lignes):
        return Referentiels(natures={'T01': Nature('T01', 'T', None, True)}, offres={'COURTE_DUREE': True},
                            comptes_argent={'FEDAPAY': True}, tiers_types={'hote': True}, moyens_paiement={})

    def etat_periode(self, mois):
        return PERIODE_VERROUILLEE if mois in self.verrouilles else 'ouverte'

    def ecrire(self, ecriture):
        # Same rule as the database: a line of an external event is written once, corrections are left out
        ref = ecriture.ligne.externe_reference
        if ref and ecriture.annule_mouvement_id is None and any(
                m.ligne.externe_reference == ref and m.annule_mouvement_id is None for m in self.lignes.values()):
            return None
        pk = len(self.lignes) + 1
        self.lignes[pk] = Mouvement(id=pk, ligne=ecriture.ligne, mois=ecriture.mois, origine=ecriture.origine,
                                    annule_mouvement_id=ecriture.annule_mouvement_id)
        return pk

    def deja_ecrite(self, ecriture):
        ref = ecriture.ligne.externe_reference
        return next((m for m in self.lignes.values() if m.ligne.externe_reference == ref), None)

    def mouvement(self, mouvement_id):
        return self.lignes.get(mouvement_id)

    def est_corrige(self, mouvement_id):
        return any(m.annule_mouvement_id == mouvement_id for m in self.lignes.values())

    def verrouiller(self, cle):
        self.verrous.append(cle)

    def a_des_lignes(self, *, externe_reference=None, reservation_id=None, transfert_id=None, location_id=None):
        return any(m.ligne.externe_reference == externe_reference or m.ligne.reservation_id == reservation_id
                   for m in self.lignes.values())

    def lignes_en_vigueur(self, nature, *, reservation_id=None, transfert_id=None, location_id=None):
        corrigees = {m.annule_mouvement_id for m in self.lignes.values()}
        return [m for m in self.lignes.values() if m.ligne.nature == nature and m.annule_mouvement_id is None
                and m.id not in corrigees and m.ligne.reservation_id == reservation_id]


class FauxParametres(Parametres):
    def lire(self, cle):
        return {'commission_hote': (Decimal('8'), True), 'events_commission': (Decimal('8'), False)}.get(cle)


class FaussesAlertes(Alertes):
    def __init__(self):
        self.envoyees = []

    def mouvement_refuse(self, origine, raison):
        self.envoyees.append(('refus', origine, raison))

    def evenement_rejoue(self, mouvement_id, nature):
        self.envoyees.append(('rejoue', mouvement_id, nature))


class FauxJournal(Journal):
    def __init__(self):
        self.corrections = []

    def correction(self, par_id, mouvement_id, inverse_id, motif):
        self.corrections.append((par_id, mouvement_id, inverse_id, motif))


class FausseTransaction(TransactionManager):
    def atomic(self):
        return nullcontext()


class Horloge(Clock):
    def now(self):
        return MAINTENANT


@pytest.fixture
def service():
    return GrandLivreService(grand_livre=FauxGrandLivre(), parametres=FauxParametres(), alertes=FaussesAlertes(),
                             journal=FauxJournal(), tx=FausseTransaction(), clock=Horloge())


LIGNE = Ligne(nature='T01', offre='COURTE_DUREE', montant=250_000, sens=ENTREE, compte_argent='FEDAPAY',
              tiers_type='hote', tiers_id=HOTE, externe_reference='TX-1')


def test_lines_are_written_and_an_event_delivered_again_is_skipped(service):
    assert service.enregistrer([LIGNE], origine='paiement') == [1]
    assert service.enregistrer([LIGNE], origine='webhook') == []
    assert service.alertes.envoyees == []


def test_an_event_delivered_again_with_another_amount_alerts(service):
    service.enregistrer([LIGNE], origine='paiement')
    service.enregistrer([replace(LIGNE, montant=1_000)], origine='webhook')
    assert service.alertes.envoyees == [('rejoue', 1, 'T01')]


def test_a_refused_line_alerts_with_its_origin_and_reason(service):
    with pytest.raises(MouvementRefuse):
        service.enregistrer([replace(LIGNE, nature='Z99')], origine='paiement')
    assert service.alertes.envoyees == [('refus', 'paiement', 'Nature « Z99 » inconnue : écriture refusée.')]


def test_a_locked_month_is_refused_and_alerts(service):
    service.grand_livre.verrouilles.add(date(2026, 12, 1))
    with pytest.raises(MouvementRefuse, match='verrouillée'):
        service.enregistrer([LIGNE], origine='paiement')
    assert service.alertes.envoyees[0][0] == 'refus' and service.grand_livre.lignes == {}


def test_a_line_without_origin_is_refused(service):
    with pytest.raises(MouvementRefuse, match='origine'):
        service.enregistrer([LIGNE], origine=' ')


def test_a_correction_writes_the_inverse_line_and_goes_to_the_journal(service):
    admin = uuid.uuid4()
    service.enregistrer([LIGNE], origine='paiement')

    inverse = service.contre_passer(1, motif='Doublon', par_id=admin)

    assert service.grand_livre.lignes[inverse].annule_mouvement_id == 1
    assert service.journal.corrections == [(admin, 1, inverse, 'Doublon')]
    # Taken before looking whether the line is already corrected: two simultaneous corrections wait for each other
    assert service.grand_livre.verrous == ['finance:correction:1']
    with pytest.raises(MouvementRefuse, match='déjà été corrigée'):
        service.contre_passer(1, motif='Encore')


def test_a_correction_of_an_unknown_line_is_refused(service):
    with pytest.raises(MouvementRefuse, match='inconnue'):
        service.contre_passer(99, motif='Rien')


def test_parameters_in_force_only(service):
    assert service.parametre('commission_hote') == Decimal('8')
    with pytest.raises(ValueError, match='inactif'):
        service.parametre('events_commission')
    with pytest.raises(ValueError, match='inconnu'):
        service.parametre('taux_invente')


def test_rectifying_cancels_the_lines_in_force_and_writes_the_right_amount(service):
    """Service fees lowered from 6 to 3 % after the payment (Stay Pack + Driver)."""
    reservation = uuid.uuid4()
    service.grand_livre.referentiels = lambda lignes: Referentiels(
        natures={'R01': Nature('R01', 'R', ENTREE, True)}, offres={'COURTE_DUREE': True},
        comptes_argent={'FEDAPAY': True}, tiers_types={}, moyens_paiement={})
    service.enregistrer([Ligne(nature='R01', offre='COURTE_DUREE', montant=15_000, sens=ENTREE,
                               compte_argent='FEDAPAY', reservation_id=reservation)], origine='paiement')

    ids = service.rectifier('R01', 7_500, motif='Pack Séjour', origine='pack_sejour',
                            objet={'reservation_id': reservation})

    inverse, nouvelle = (service.grand_livre.lignes[i] for i in ids)
    assert (inverse.annule_mouvement_id, inverse.ligne.montant) == (1, 15_000)
    assert (nouvelle.ligne.montant, nouvelle.ligne.sens, nouvelle.ligne.motif) == (7_500, ENTREE, 'Pack Séjour')
    with pytest.raises(MouvementRefuse, match='rien à rectifier'):
        service.rectifier('R02', 0, motif='x', origine='x', objet={'reservation_id': reservation})
