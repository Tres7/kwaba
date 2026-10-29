"""PDF of a contract: text, signature block, then electronic signature certificate."""
from datetime import UTC
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, PageBreak, Spacer, Table, TableStyle

from apps.documents.api import Document, date, paragraphe as _p, societe as _societe

from .models import ContratModel
from .services import blocs

LARGEUR_SIGNATURE, HAUTEUR_SIGNATURE = 60 * mm, 22 * mm
TITRES_PARTIE = {'hote': "L'Hôte", 'hotel': "L'Établissement", 'loueur': 'Le Propriétaire', 'chauffeur': 'Le Chauffeur',
                 'ong': "L'Association"}


def _image(fichier) -> Image | None:
    if not fichier:
        return None
    with fichier.open('rb') as f:
        contenu = f.read()
    image = Image(BytesIO(contenu))
    # Proportions kept in the signature frame
    echelle = min(LARGEUR_SIGNATURE / image.imageWidth, HAUTEUR_SIGNATURE / image.imageHeight)
    image.drawWidth, image.drawHeight = image.imageWidth * echelle, image.imageHeight * echelle
    image.hAlign = 'LEFT'
    return image


def _colonne(titre: str, image, lignes: list[str]) -> list:
    return [_p(titre, 'gras'), Spacer(0, 2 * mm), image or Spacer(0, HAUTEUR_SIGNATURE), Spacer(0, 2 * mm),
            *[_p(ligne, 'petit') for ligne in lignes if ligne]]


def contrat_pdf(c: ContratModel) -> bytes:
    societe = _societe()
    signe = c.statut == 'signe'
    doc = Document(c.titre, c.reference, sous_titre=(f"signé le {date(c.signe_le)}" if signe else
                                                     f"émis le {date(c.cree_le)} · projet en attente de signature"))
    for bloc in blocs(c.corps):
        if bloc['type'] == 'titre':
            doc.ajouter(_p(bloc['texte'], 'section'))
        else:
            doc.ajouter(_p(bloc['texte'], 'justifie'))

    # Signatures: Kwa-Ba (legal representative, when issued) and the party
    kwaba = _colonne('Pour Kwa-Ba', _image(societe.signature_representant), [
        societe.raison_sociale or societe.nom_commercial,
        ', '.join(x for x in (societe.representant_nom, societe.representant_qualite) if x),
        f"Émis électroniquement le {date(c.cree_le, 'j F Y à H:i')}",
    ])
    partie = _colonne(f"Pour {TITRES_PARTIE[c.type][0].lower()}{TITRES_PARTIE[c.type][1:]}",
                      _image(c.signature) if signe else None,
                      [c.partie_nom, f"Signé électroniquement par {c.signataire_nom} le {date(c.signe_le, 'j F Y à H:i')}",
                       "« Lu et approuvé »"] if signe else [c.partie_nom, "En attente de signature"])
    tableau = Table([[kwaba, partie]], colWidths=[85 * mm, 85 * mm])
    tableau.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                 ('BOX', (0, 0), (0, 0), 0.4, colors.HexColor('#E5E7EB')),
                                 ('BOX', (1, 0), (1, 0), 0.4, colors.HexColor('#E5E7EB')),
                                 ('LEFTPADDING', (0, 0), (-1, -1), 4 * mm), ('TOPPADDING', (0, 0), (-1, -1), 3 * mm),
                                 ('BOTTOMPADDING', (0, 0), (-1, -1), 3 * mm)]))
    doc.ajouter(Spacer(0, 6 * mm), KeepTogether([_p('Signatures', 'section'), tableau]))

    if signe:
        doc.ajouter(PageBreak(), _p('Certificat de signature électronique', 'titre'), Spacer(0, 3 * mm),
                    _p("Ce certificat fait partie intégrante du contrat. Il rassemble les éléments qui permettent "
                       "d'identifier le signataire et de vérifier que le document n'a pas été modifié.", 'petit'))
        doc.bloc('Document', [
            ('Contrat', f"{c.titre}, {c.reference}"), ('Modèle', f"version {c.version_modele}"),
            ('Émis le', date(c.cree_le, 'j F Y à H:i')), ('Émetteur', c.kwaba_signataire),
            ('Empreinte du texte', f"SHA-256 {c.empreinte_texte}"),
        ])
        doc.bloc('Signataire', [
            ('Partie', f"{c.partie_nom} ({c.get_type_display()})"), ('Nom tapé', c.signataire_nom),
            ('Email', c.partie_email), ('Téléphone', c.partie_telephone),
            ('Authentification', "Lien personnel à usage unique envoyé à l'adresse email ci-dessus" if c.methode == 'lien personnel'
             else 'Compte Kwa-Ba du signataire, connecté'),
            ('Consentement', "Case « J'ai lu le contrat et je l'accepte ; je reconnais que ma signature électronique "
                             "a la même valeur qu'une signature manuscrite » cochée avant la signature"),
        ])
        doc.bloc('Horodatage et appareil', [
            ('Date et heure', f"{c.signe_le.astimezone(UTC):%d/%m/%Y à %H:%M:%S} UTC (temps universel)"),
            ('Adresse IP', c.ip or '-'), ('Navigateur', c.user_agent or '-'),
        ])
        doc.paragraphe("L'empreinte SHA-256 du PDF signé, calculée après sa génération, est conservée par Kwa-Ba et "
                       "communiquée dans l'email de confirmation : tout PDF dont l'empreinte diffère a été modifié.", 'petit')
    return doc.en_pdf()
