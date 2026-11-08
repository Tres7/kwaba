"""Host (B1) and hotel (B2) contracts: the rates become variables filled with the rates set in the back-office
(paiements.ReglagesTarifsModel), and the cleaning fee follows the Kwa-Ba scale (article 3.1 of B1).

A template is updated only if it still holds the original text: a text changed in the back-office is not touched.
The contracts already issued keep the text of their version."""
from django.db import migrations

REMPLACEMENTS = {
    'hote': [("3.1. L'Hôte fixe librement son prix par nuit et ses frais de ménage éventuels.", "3.1. L'Hôte fixe librement son prix par nuit. Les frais de ménage suivent le barème de KWA-BA selon le type de logement ({{ tarifs.frais_menage }}) : payés par le client, ils sont reversés en totalité à l'Hôte, sans commission."), ('– Commission de KWA-BA : 8 % du prix des nuits (hors frais de service payés par le client).', '– Commission de KWA-BA : {{ tarifs.commission_hote }} du prix des nuits (hors frais de service et frais de ménage payés par le client).'), ('– Programme Fondateurs (50 premiers hôtes) : 5 % pendant 6 mois ; {{ partie.fondateur }}.', '– Programme Fondateurs (50 premiers hôtes) : {{ tarifs.commission_fondateur }} pendant 6 mois ; {{ partie.fondateur }}.'), ("– Frais de service du client (6 %, 3 % en Pack Séjour ou en Client fidèle, 4 % entreprises) : payés par le client, ils ne réduisent pas le revenu de l'Hôte.", "– Frais de service du client ({{ tarifs.frais_voyageur }}, {{ tarifs.frais_reduits }} en Pack Séjour ou en Client fidèle, 4 % entreprises) : payés par le client, ils ne réduisent pas le revenu de l'Hôte.")],
    'hotel': [("– Commission de KWA-BA : 12 % du prix de l'hébergement, hors taxe de séjour éventuelle.", "– Commission de KWA-BA : {{ tarifs.commission_hotel }} du prix de l'hébergement, hors taxe de séjour éventuelle."), ("– Frais de service du client (6 %, 3 % en Pack Séjour ou en Client fidèle, 4 % entreprises) : payés par le client, ils ne réduisent pas le revenu de l'Établissement.", "– Frais de service du client ({{ tarifs.frais_voyageur }}, {{ tarifs.frais_reduits }} en Pack Séjour ou en Client fidèle, 4 % entreprises) : payés par le client, ils ne réduisent pas le revenu de l'Établissement.")],
}


def appliquer(apps, schema_editor, sens=1):
    Modele = apps.get_model('contrats', 'ModeleContratModel')
    for type_contrat, paires in REMPLACEMENTS.items():
        paires = [(a, b) if sens == 1 else (b, a) for a, b in paires]
        for modele in Modele.objects.filter(type=type_contrat):
            corps = modele.corps.replace('\r\n', '\n')
            if not all(a in corps for a, _ in paires):
                continue
            for a, b in paires:
                corps = corps.replace(a, b)
            modele.corps, modele.version = corps, modele.version + 1
            modele.save(update_fields=['corps', 'version'])


def annuler(apps, schema_editor):
    appliquer(apps, schema_editor, sens=-1)


class Migration(migrations.Migration):
    dependencies = [('contrats', '0008_comptes_par_identifiant')]
    operations = [migrations.RunPython(appliquer, annuler)]
