"""Public site settings: module switches and legal numbers (settings.MODULES, settings.MENTIONS_LEGALES and
settings.SOCIETE_EN_FORMATION).

They come from the API environment, so a restart of the API is enough to change them: the website reads them from
GET /api/v1/site/ (menus, footer, sitemap, redirects of masked pages, legal notices).
"""
from django.conf import settings
from django.http import JsonResponse
from rest_framework.exceptions import NotFound


def module_actif(nom: str) -> bool:
    return bool(settings.MODULES.get(nom))


def exiger_module(nom: str) -> None:
    """To call first in the API views of a module: a masked module answers as if it did not exist."""
    if not module_actif(nom):
        raise NotFound()


def mentions_legales() -> dict[str, str]:
    from apps.documents.models import ParametresSocieteModel

    mentions = {cle: valeur.strip() for cle, valeur in settings.MENTIONS_LEGALES.items()}
    if not (mentions['rccm'] and mentions['nif']):
        societe = ParametresSocieteModel.objects.filter(pk=1).first()
        if societe:
            mentions['rccm'] = mentions['rccm'] or societe.rccm.strip()
            mentions['nif'] = mentions['nif'] or societe.nif.strip()
    return mentions


def site(request):
    return JsonResponse({
        'modules': {nom: bool(actif) for nom, actif in settings.MODULES.items()},
        'mentions': mentions_legales(),
        'en_formation': settings.SOCIETE_EN_FORMATION,
        'contact_email': settings.ASSISTANCE_CONTACT,
    })
