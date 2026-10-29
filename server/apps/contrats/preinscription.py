"""Pre-registration of hosts during the pre-launch (config/prelancement.py).

Before creating a listing, a host accepts this text. A new wording must get a new VERSION: hosts then accept it again
before their next listing. The site displays the text returned by the API, so the fingerprint recorded is the one of
the exact text the host read.
"""
import hashlib

from config import prelancement

from .models import PreinscriptionModel

VERSION = 1
TEXTES = {
    'fr': (
        "Kwa-Ba est exploitée par Kwaba SAS, société en cours d'immatriculation au Togo. En vous pré-inscrivant, "
        "vous confirmez que les informations de votre annonce sont exactes et que vous êtes autorisé à louer ce "
        "logement. Votre annonce ne sera publiée qu'après la signature du contrat hôte définitif, qui vous sera "
        "envoyé dès l'immatriculation de la société. Aucun paiement ni aucune réservation n'aura lieu avant cette "
        "signature."
    ),
    'en': (
        "Kwa-Ba is operated by Kwaba SAS, a company being registered in Togo. By pre-registering, you confirm that "
        "the information in your listing is accurate and that you are authorised to rent out this property. Your "
        "listing will only be published once you have signed the final host agreement, which will be sent to you as "
        "soon as the company is registered. No payment or booking will take place before this signature."
    ),
}
LANGUES = tuple(TEXTES)


def langue_de(valeur: str) -> str:
    return 'en' if (valeur or '').lower().startswith('en') else 'fr'


def empreinte(langue: str) -> str:
    return hashlib.sha256(TEXTES[langue].encode()).hexdigest()


def acceptee(hote) -> bool:
    return PreinscriptionModel.objects.filter(hote_id=hote.pk, version=VERSION).exists()


def requise(utilisateur) -> bool:
    """Must this user accept the current text before creating a listing? Only hosts, only during the pre-launch."""
    return prelancement.actif() and utilisateur.role == 'hote' and not acceptee(utilisateur)


def accepter(hote, *, langue: str, ip: str | None, user_agent: str) -> PreinscriptionModel:
    """Records the acceptance of the current version (idempotent: a second acceptance keeps the first proof)."""
    preinscription, _ = PreinscriptionModel.objects.get_or_create(
        hote_id=hote.pk, version=VERSION,
        defaults={'langue': langue, 'empreinte_texte': empreinte(langue), 'ip': ip, 'user_agent': (user_agent or '')[:300]},
    )
    return preinscription
