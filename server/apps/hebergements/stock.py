"""Stock of the unit types (TypeLogementModel), night by night.

A type is available over [debut, fin) for `nb` units if, FOR EACH NIGHT from debut to fin - 1 (the departure day is
excluded), its quantity minus the units held by active bookings covering that night is at least `nb`, and no
closure covers that night (a closure without a type closes the whole establishment).

Active bookings: confirmed, or waiting for a payment that has not expired (given by the reservations module). A booking
without a unit type (data written before the types) counts against every type of its establishment: never too few.

Everything is read in two queries (bookings, closures) whatever the number of types and nights.
"""
from collections import defaultdict
from datetime import date, timedelta
from typing import Iterable

from .models import BlocageModel, TypeLogementModel
from .occupations import reservations


def nuits(debut: date, fin: date) -> list[date]:
    """The nights of a stay [debut, fin): debut, debut + 1, …, fin - 1."""
    return [debut + timedelta(days=i) for i in range((fin - debut).days)]


class Occupation:
    """Units taken and closed nights of some unit types over [debut, fin), read once."""

    def __init__(self, types: Iterable[TypeLogementModel], debut: date, fin: date, exclure=None):
        self.types = {t.id: t for t in types}
        self.debut, self.fin = debut, fin
        etablissements = {t.hebergement_id for t in self.types.values()}
        self.prises: dict = defaultdict(lambda: defaultdict(int))   # type id -> night -> units taken
        self.fermees: dict = defaultdict(set)                        # type id -> closed nights
        if not self.types or fin <= debut:
            return

        par_etablissement = defaultdict(list)
        for t in self.types.values():
            par_etablissement[t.hebergement_id].append(t.id)

        for r in reservations().actives(etablissements, debut, fin, exclure):
            if r['type_logement_id'] and r['type_logement_id'] not in self.types:
                continue
            concernes = [r['type_logement_id']] if r['type_logement_id'] else par_etablissement[r['hebergement_id']]
            for nuit in nuits(max(r['check_in'], debut), min(r['check_out'], fin)):
                for type_id in concernes:
                    self.prises[type_id][nuit] += r['nb_unites'] or 1

        blocages = BlocageModel.objects.filter(hebergement_id__in=etablissements, debut__lt=fin, fin__gt=debut)
        for b in blocages.only('hebergement_id', 'type_logement_id', 'debut', 'fin'):
            concernes = [b.type_logement_id] if b.type_logement_id else par_etablissement[b.hebergement_id]
            for nuit in nuits(max(b.debut, debut), min(b.fin, fin)):
                for type_id in concernes:
                    if type_id in self.types:
                        self.fermees[type_id].add(nuit)

    def restantes_nuit(self, type_id, nuit: date) -> int:
        """Units still bookable that night (0 if closed)."""
        if nuit in self.fermees[type_id]:
            return 0
        return max(0, self.types[type_id].quantite - self.prises[type_id][nuit])

    def restantes(self, type_id, debut: date | None = None, fin: date | None = None) -> int:
        """Units bookable for the whole period: the minimum over its nights."""
        periode = nuits(debut or self.debut, fin or self.fin)
        if not periode:
            return 0
        return min(self.restantes_nuit(type_id, n) for n in periode)

    def ferme(self, type_id, debut: date | None = None, fin: date | None = None) -> bool:
        return any(n in self.fermees[type_id] for n in nuits(debut or self.debut, fin or self.fin))

    def nuits_completes(self, type_id) -> list[date]:
        """Nights of the window when no unit of this type is left."""
        return [n for n in nuits(self.debut, self.fin) if self.restantes_nuit(type_id, n) == 0]


def restantes(type_logement: TypeLogementModel, debut: date, fin: date, exclure=None) -> int:
    return Occupation([type_logement], debut, fin, exclure).restantes(type_logement.id)


def est_disponible(type_logement: TypeLogementModel, debut: date, fin: date, nb: int = 1, exclure=None) -> bool:
    return restantes(type_logement, debut, fin, exclure) >= nb


def prochaine_date(type_logement: TypeLogementModel, debut: date, duree: int, nb: int = 1, horizon: int = 60) -> date | None:
    """First arrival date from `debut` (within `horizon` days) for a stay of `duree` nights with `nb` units."""
    occupation = Occupation([type_logement], debut, debut + timedelta(days=horizon + duree))
    for i in range(horizon + 1):
        arrivee = debut + timedelta(days=i)
        if occupation.restantes(type_logement.id, arrivee, arrivee + timedelta(days=duree)) >= nb:
            return arrivee
    return None


# Search: how far the next possible arrival is looked for, in days
HORIZON_PROCHAINE_DATE = 60


def disponibilites_etablissements(hebergement_ids, debut: date, fin: date, horizon: int = HORIZON_PROCHAINE_DATE) -> dict:
    """For a search with dates, per establishment: can it be booked over [debut, fin), how many units are left
    (all its types together), and if it is full, the next arrival date for a stay of the same length.

    Read in two queries for all the establishments (bookings and closures over the period plus the horizon).
    """
    types = list(TypeLogementModel.objects.filter(hebergement_id__in=list(hebergement_ids), actif=True))
    duree = (fin - debut).days
    occupation = Occupation(types, debut, debut + timedelta(days=horizon + duree))
    par_etablissement = defaultdict(list)
    for t in types:
        par_etablissement[t.hebergement_id].append(t)

    resultat = {}
    for hebergement_id, siens in par_etablissement.items():
        restantes = {t.id: occupation.restantes(t.id, debut, fin) for t in siens}
        disponible = any(n >= 1 for n in restantes.values())
        prochaine = None
        if not disponible:
            for i in range(1, horizon + 1):
                arrivee = debut + timedelta(days=i)
                if any(occupation.restantes(t.id, arrivee, arrivee + timedelta(days=duree)) >= 1 for t in siens):
                    prochaine = arrivee
                    break
        resultat[hebergement_id] = {
            'disponible': disponible,
            'unites_restantes': sum(restantes.values()),
            'unites_total': sum(t.quantite for t in siens),
            'prochaine_date': prochaine,
        }
    return resultat
