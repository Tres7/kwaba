"""Finance CSV export: a cell that starts like a formula stays text (security audit of 2026-11-07, lead 19)."""
from apps.paiements.finances import en_csv


def test_cellule_qui_commence_comme_une_formule_ecrite_en_texte():
    donnees = {
        'encaissements': [{'date': None, 'produit': 'reservation', 'reference': 'RES-1', 'prestataire': 'fedapay',
                           'mode': '', 'montant': 1000, 'libelle': '=HYPERLINK("https://x.invalid";"x")'}],
        'remboursements': [],
        'versements': [{'envoye_le': None, 'date_prevue': None, 'categorie': 'Hôte', 'beneficiaire': '@SUM(A1:A9)',
                        'objet': 'RES-1', 'montant': 900, 'commission': 100, 'statut': 'planifie'}],
    }
    lignes = en_csv(donnees).decode('utf-8-sig').splitlines()
    assert "'=HYPERLINK" in lignes[1] and ";=HYPERLINK" not in lignes[1] and ';"=HYPERLINK' not in lignes[1]
    assert ";'@SUM(A1:A9);" in lignes[2]
    assert ';-900;100;' in lignes[2]  # amounts stay numbers
