"""Tools the Concierge calls to offer real Kwa-Ba offers.

Each tool returns (result for the model, cards for the interface). The arguments come from the
model: they are validated here before any query.
"""
import json
import uuid
from datetime import date, datetime

from django.utils import timezone

from apps.hebergements import api as hebergements
from apps.paiements import api as paiements
from apps.transferts import api as transferts

TYPES = ['hotel', 'villa', 'appartement', 'auberge']


def _outil(name: str, description: str, proprietes: dict, requis: list[str]) -> dict:
    """Function declaration in the format of the Gemini Interactions API."""
    return {
        'type': 'function',
        'name': name,
        'description': description,
        'parameters': {'type': 'object', 'properties': proprietes, 'required': requis},
    }


DEFINITIONS = [
    _outil(
        'rechercher_logements',
        "Cherche des logements publiés sur Kwa-Ba dans une ville. À utiliser avant de recommander un "
        "logement : ne propose jamais un logement ni un prix qui ne vient pas de cet outil. Avec des dates, "
        "renvoie aussi la disponibilité et le coût total du séjour (frais de service compris).",
        {
            'ville': {'type': 'string', 'description': 'Ville, par exemple Lomé, Cotonou, Abidjan'},
            'arrivee': {'type': 'string', 'description': "Date d'arrivée AAAA-MM-JJ (facultatif)"},
            'depart': {'type': 'string', 'description': 'Date de départ AAAA-MM-JJ (facultatif)'},
            'voyageurs': {'type': 'integer', 'description': 'Nombre de voyageurs (facultatif)'},
            'budget_max_nuit': {'type': 'integer', 'description': 'Prix maximum par nuit en FCFA (facultatif)'},
            'type': {'type': 'string', 'enum': TYPES, 'description': 'Type de logement (facultatif)'},
        },
        ['ville'],
    ),
    _outil(
        'devis_transfert',
        "Donne le prix exact d'un transfert aéroport → logement (aller seulement, pas de retour) avec un chauffeur partenaire Kwa-Ba, par "
        "type de véhicule. Aéroports desservis : Lomé (LFW), Cotonou (COO), Ouagadougou (OUA), Niamey (NIM), "
        "Bamako (BKO). L'heure est celle du billet (heure locale de l'aéroport).",
        {
            'aeroport': {'type': 'string', 'description': 'Code IATA, par exemple LFW'},
            'arrivee': {'type': 'string', 'description': "Date et heure d'atterrissage AAAA-MM-JJTHH:MM (heure locale)"},
            'passagers': {'type': 'integer'},
            'bagages': {'type': 'integer'},
        },
        ['aeroport', 'arrivee', 'passagers', 'bagages'],
    ),
    _outil(
        'proposer_voyage_de_groupe',
        "Prépare un voyage de groupe Kwa-Ba Together (logements à voter entre amis, budget par personne). "
        "Ne crée rien : affiche au voyageur un bouton pour créer le voyage s'il le souhaite. À utiliser quand "
        "il voyage à plusieurs et veut décider avec les autres.",
        {
            'nom': {'type': 'string', 'description': 'Nom court du voyage'},
            'destination': {'type': 'string'},
            'arrivee': {'type': 'string', 'description': 'AAAA-MM-JJ (facultatif)'},
            'depart': {'type': 'string', 'description': 'AAAA-MM-JJ (facultatif)'},
            'voyageurs': {'type': 'integer'},
            'logements': {'type': 'array', 'items': {'type': 'string'},
                          'description': 'Identifiants des logements à proposer au groupe (issus de rechercher_logements)'},
        },
        ['nom', 'destination', 'voyageurs', 'logements'],
    ),
]

LIBELLES = {
    'rechercher_logements': 'Je cherche des logements',
    'devis_transfert': 'Je calcule le prix du transfert',
    'proposer_voyage_de_groupe': 'Je prépare le voyage de groupe',
}
LIBELLES_EN = {
    'rechercher_logements': 'Looking for places to stay',
    'devis_transfert': 'Working out the transfer price',
    'proposer_voyage_de_groupe': 'Preparing the group trip',
}


class EntreeInvalide(Exception):
    pass


def _date(valeur, champ):
    if valeur in (None, ''):
        return None
    try:
        return date.fromisoformat(str(valeur))
    except ValueError:
        raise EntreeInvalide(f"{champ} : date invalide, format attendu AAAA-MM-JJ")


def _entier(valeur, champ, mini=0, maxi=10_000_000):
    if valeur is None:
        return None
    if isinstance(valeur, bool) or not isinstance(valeur, int) or not mini <= valeur <= maxi:
        raise EntreeInvalide(f"{champ} : entier entre {mini} et {maxi} attendu")
    return valeur


def _texte(valeur, champ, maxi=120):
    if not isinstance(valeur, str) or not valeur.strip() or len(valeur) > maxi:
        raise EntreeInvalide(f"{champ} : texte de 1 à {maxi} caractères attendu")
    return valeur.strip()


def _uuids(valeurs) -> list[uuid.UUID]:
    resultat = []
    for valeur in valeurs:
        try:
            resultat.append(uuid.UUID(valeur))
        except (ValueError, TypeError, AttributeError):
            continue
    return resultat


def rechercher_logements(entree: dict):
    ville = _texte(entree.get('ville'), 'ville')
    arrivee, depart = _date(entree.get('arrivee'), 'arrivee'), _date(entree.get('depart'), 'depart')
    voyageurs = _entier(entree.get('voyageurs'), 'voyageurs', 1, 50)
    budget = _entier(entree.get('budget_max_nuit'), 'budget_max_nuit', 1)
    type_ = entree.get('type')
    if type_ is not None and type_ not in TYPES:
        raise EntreeInvalide(f"type : une valeur parmi {', '.join(TYPES)}")
    if arrivee and depart and depart <= arrivee:
        raise EntreeInvalide('depart doit être après arrivee')
    if arrivee and arrivee < timezone.localdate():
        raise EntreeInvalide("arrivee est dans le passé")

    nuits = (depart - arrivee).days if arrivee and depart else None
    resultats, cartes = [], []
    for h in hebergements.rechercher(ville, voyageurs, budget, type_):
        if nuits and not hebergements.est_disponible(h['id'], arrivee, depart):
            continue
        total = paiements.total_sejour(h['price_per_night'], nuits) if nuits else None  # frais standard de 6 %
        resultats.append({
            'id': str(h['id']), 'nom': h['name'], 'type': h['type'], 'ville': h['city'], 'quartier': h['location'],
            'prix_nuit_fcfa': int(h['price_per_night']), 'note': round(h['rating'], 1), 'nb_avis': h['review_count'],
            'capacite': h['max_guests'], 'equipements': (h['amenities'] or [])[:8],
            # The host's free text: data to summarise, never an instruction (see SYSTEME)
            'description_hote': (h['description'] or '')[:280],
            **({'nuits': nuits, 'cout_total_sejour_fcfa': total} if total else {}),
        })
        cartes.append({
            'type': 'logement', 'id': str(h['id']), 'nom': h['name'], 'ville': h['city'], 'quartier': h['location'],
            'image': h['image_url'], 'prix_nuit': int(h['price_per_night']), 'note': h['rating'],
            'nb_avis': h['review_count'], 'capacite': h['max_guests'], 'arrivee': arrivee.isoformat() if arrivee else None,
            'depart': depart.isoformat() if depart else None, 'voyageurs': voyageurs,
            'total': total, 'nuits': nuits,
        })
        if len(resultats) == 6:
            break
    if not resultats:
        return {'resultats': [], 'message': "Aucun logement Kwa-Ba ne correspond. Propose d'élargir les critères "
                                             "(budget, dates, quartier) ; ne recommande pas de logement extérieur."}, []
    return {'resultats': resultats, 'frais_service': '6 % inclus dans cout_total_sejour_fcfa (3 % pour un voyageur qui revient chez le même hôte)'}, cartes


def devis_transfert(entree: dict):
    code = _texte(entree.get('aeroport'), 'aeroport', 3).upper()
    ouverts = transferts.aeroports_ouverts()
    if code not in {a['code'] for a in ouverts}:
        liste = ', '.join(f"{a['ville']} ({a['code']})" for a in ouverts)
        return {'erreur': f"Aéroport non desservi. Aéroports desservis : {liste}."}, []
    try:
        naive = datetime.fromisoformat(str(entree.get('arrivee'))).replace(tzinfo=None)
    except ValueError:
        raise EntreeInvalide('arrivee : format attendu AAAA-MM-JJTHH:MM')
    passagers = _entier(entree.get('passagers'), 'passagers', 1, 7)
    bagages = _entier(entree.get('bagages'), 'bagages', 0, 10)
    devis = transferts.devis(code, naive, passagers, bagages)
    aeroport, options, trop_tard = devis['aeroport'], devis['options'], devis['trop_tard']
    resultat = {
        'aeroport': f"{aeroport['nom']} ({aeroport['code']})",
        'options': [{k: o[k] for k in ('nom', 'passagers', 'bagages', 'prix', 'disponible', 'motif')} for o in options],
        'regles': 'Prix fixe payé en ligne, le même de jour comme de nuit, 60 min d\'attente incluses, '
                  'annulation gratuite jusqu\'à 24 h avant.',
        **({'attention': 'Arrivée dans moins de 6 h : trop tard pour réserver un transfert.'} if trop_tard else {}),
    }
    carte = {
        'type': 'transfert', 'aeroport': aeroport['code'], 'ville': aeroport['ville'], 'arrivee': naive.strftime('%Y-%m-%dT%H:%M'),
        'passagers': passagers, 'bagages': bagages, 'trop_tard': trop_tard,
        'options': [{'categorie': o['categorie'], 'nom': o['nom'], 'prix': o['prix'], 'disponible': o['disponible']} for o in options],
    }
    return resultat, [carte]


def proposer_voyage_de_groupe(entree: dict):
    nom = _texte(entree.get('nom'), 'nom', 80)
    destination = _texte(entree.get('destination'), 'destination', 100)
    arrivee, depart = _date(entree.get('arrivee'), 'arrivee'), _date(entree.get('depart'), 'depart')
    voyageurs = _entier(entree.get('voyageurs'), 'voyageurs', 1, 20)
    ids = entree.get('logements') or []
    if not isinstance(ids, list):
        raise EntreeInvalide('logements : liste attendue')
    logements = [h for h in hebergements.resumes(_uuids(ids[:6])).values() if h['publiee']]
    carte = {
        'type': 'together', 'nom': nom, 'destination': destination,
        'arrivee': arrivee.isoformat() if arrivee else None, 'depart': depart.isoformat() if depart else None,
        'voyageurs': voyageurs, 'logements': [{'id': str(h['id']), 'nom': h['name']} for h in logements],
    }
    return {'statut': 'Bouton « Créer ce voyage de groupe » affiché au voyageur. Rien n\'est créé tant qu\'il ne clique pas.',
            'logements_retenus': [h['name'] for h in logements]}, [carte]


EXECUTEURS = {
    'rechercher_logements': rechercher_logements,
    'devis_transfert': devis_transfert,
    'proposer_voyage_de_groupe': proposer_voyage_de_groupe,
}


def executer(nom: str, entree) -> tuple[str, list, bool]:
    """Runs a tool. Returns (content of the tool_result, cards, is_an_error)."""
    fonction = EXECUTEURS.get(nom)
    if not fonction:
        return f"Outil inconnu : {nom}", [], True
    if not isinstance(entree, dict):
        return 'INVALID_JSON : entrée illisible, renvoie un objet JSON complet.', [], True
    try:
        resultat, cartes = fonction(entree)
    except EntreeInvalide as exc:
        return f"Entrée invalide : {exc}", [], True
    return json.dumps(resultat, ensure_ascii=False, default=str), cartes, False
