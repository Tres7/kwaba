"""Layout of the Kwa-Ba documents (ReportLab): logo, company information, blocks, tables, footer."""
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from django.utils import formats, timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import ParametresSocieteModel

LOGO = Path(__file__).with_name('assets') / 'kwaba-logo.png'
VERT, AMBRE, ENCRE, GRIS, CREME = (colors.HexColor(c) for c in ('#0E4D47', '#F59E0B', '#1F2937', '#6B7280', '#F8F6F2'))

_base = ParagraphStyle('base', fontName='Helvetica', fontSize=9.5, leading=13, textColor=ENCRE)
STYLES = {
    'base': _base,
    'petit': ParagraphStyle('petit', parent=_base, fontSize=8, leading=10.5, textColor=GRIS),
    'titre': ParagraphStyle('titre', parent=_base, fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=VERT),
    'sous_titre': ParagraphStyle('sous_titre', parent=_base, fontSize=10, textColor=GRIS),
    'section': ParagraphStyle('section', parent=_base, fontName='Helvetica-Bold', fontSize=10.5, textColor=VERT, spaceBefore=8, spaceAfter=4),
    'droite': ParagraphStyle('droite', parent=_base, alignment=TA_RIGHT),
    'gras': ParagraphStyle('gras', parent=_base, fontName='Helvetica-Bold'),
    'emetteur': ParagraphStyle('emetteur', parent=_base, fontSize=8, leading=10.5, textColor=GRIS, alignment=TA_RIGHT),
    'total': ParagraphStyle('total', parent=_base, alignment=TA_RIGHT, fontName='Helvetica-Bold', textColor=colors.white),
    'justifie': ParagraphStyle('justifie', parent=_base, alignment=TA_JUSTIFY, spaceAfter=4),
}


def fcfa(montant) -> str:
    return f"{int(montant):,}".replace(',', ' ') + ' FCFA'


def date(valeur, fmt='j F Y') -> str:
    if valeur is None:
        return '-'
    if hasattr(valeur, 'tzinfo') and getattr(valeur, 'hour', None) is not None:
        valeur = timezone.localtime(valeur)
    return formats.date_format(valeur, fmt)


def _p(texte, style='base'):
    # The text comes from the database: ReportLab's special characters are escaped
    texte = str(texte).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
    return Paragraph(texte, STYLES[style])


@dataclass
class Document:
    """A document: title, reference, then blocks ("label: value" lines) and amount tables."""
    titre: str
    reference: str
    sous_titre: str = ''
    destinataire: list[str] = field(default_factory=list)
    elements: list = field(default_factory=list)
    mentions: str = ''

    def bloc(self, titre: str, lignes: list[tuple[str, str]]):
        self.elements.append(_p(titre, 'section'))
        donnees = [[_p(libelle, 'petit'), _p(valeur)] for libelle, valeur in lignes if valeur not in (None, '')]
        tableau = Table(donnees, colWidths=[45 * mm, 125 * mm])
        tableau.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                                     ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
        self.elements.append(tableau)

    def montants(self, lignes: list[tuple[str, str, str, str]], totaux: list[tuple[str, str]]):
        """Lines (description, quantity, unit price, total) then totals (label, amount), the last one highlighted."""
        entete = [_p(t, 'gras') for t in ('Désignation', 'Qté', 'Prix unitaire', 'Total')]
        corps = [[_p(d), _p(q, 'droite'), _p(pu, 'droite'), _p(t, 'droite')] for d, q, pu, t in lignes]
        pied = [['', '', _p(libelle, 'total' if i == len(totaux) - 1 else 'droite'), _p(montant, 'total' if i == len(totaux) - 1 else 'droite')]
                for i, (libelle, montant) in enumerate(totaux)]
        tableau = Table([entete, *corps, *pied], colWidths=[90 * mm, 15 * mm, 32 * mm, 33 * mm])
        n = len(corps)
        tableau.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), CREME), ('LINEBELOW', (0, 0), (-1, 0), 0.6, VERT),
            ('LINEBELOW', (0, n), (-1, n), 0.4, colors.HexColor('#E5E7EB')),
            ('BACKGROUND', (2, -1), (-1, -1), VERT), ('TEXTCOLOR', (2, -1), (-1, -1), colors.white),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        self.elements.append(Spacer(0, 4 * mm))
        self.elements.append(tableau)

    def ajouter(self, *elements):
        """Any ReportLab elements (tables, images, page breaks…)."""
        self.elements.extend(elements)

    def paragraphe(self, texte: str, style='base'):
        self.elements.append(Spacer(0, 3 * mm))
        self.elements.append(_p(texte, style))

    def en_pdf(self) -> bytes:
        societe = ParametresSocieteModel.courants()
        tampon = BytesIO()
        doc = SimpleDocTemplate(tampon, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                                bottomMargin=24 * mm, title=f"{self.titre} {self.reference}", author=societe.nom_commercial)

        emetteur = [societe.raison_sociale or societe.nom_commercial, societe.forme_juridique, societe.adresse,
                    societe.pays, ' · '.join(x for x in (societe.telephone, societe.email) if x),
                    ' · '.join(x for x in (f"NIF {societe.nif}" if societe.nif else '', f"RCCM {societe.rccm}" if societe.rccm else '') if x)]
        logo = Image(str(LOGO), width=42 * mm, height=42 * mm * 240 / 1000)
        entete = Table([[logo, _p('\n'.join(x for x in emetteur if x), 'emetteur')]], colWidths=[85 * mm, 85 * mm])
        entete.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                                    ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
        titre = [_p(self.titre, 'titre'), _p(f"Référence {self.reference}" + (f" · {self.sous_titre}" if self.sous_titre else ''), 'sous_titre')]
        histoire = [entete, Spacer(0, 10 * mm), *titre]
        if self.destinataire:
            histoire += [Spacer(0, 5 * mm), _p('Pour', 'petit'), _p('\n'.join(self.destinataire), 'gras')]
        histoire += [Spacer(0, 4 * mm), *self.elements]
        mentions = self.mentions or societe.mentions

        def pied(canvas, d):
            canvas.saveState()
            canvas.setStrokeColor(AMBRE)
            canvas.setLineWidth(1.2)
            canvas.line(20 * mm, 17 * mm, A4[0] - 20 * mm, 17 * mm)
            canvas.setFont('Helvetica', 7.5)
            canvas.setFillColor(GRIS)
            texte = (mentions.replace('\n', ' ') + '  ·  ' if mentions else '') + f"{societe.site} · document généré le {date(timezone.now(), 'j F Y à H:i')}"
            canvas.drawString(20 * mm, 12 * mm, texte[:150])
            canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {d.page}")
            canvas.restoreState()

        doc.build(histoire, onFirstPage=pied, onLaterPages=pied)
        return tampon.getvalue()
