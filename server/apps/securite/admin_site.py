"""Sign-in to the Django administration: attempts limited per IP address and per email, failures logged."""
from django.contrib import admin
from django.http import HttpResponse

from .audit import journaliser
from .limites import Tentatives, ip_client

MAX_ECHECS_IP = 20
MAX_ECHECS_EMAIL = 5
FENETRE = 15 * 60


def connexion_admin(request, extra_context=None):
    if request.method != 'POST':
        return admin.site.login(request, extra_context)

    email = str(request.POST.get('username', '')).strip().lower()
    compteurs = [
        Tentatives(f"admin:ip:{ip_client(request) or 'inconnue'}", MAX_ECHECS_IP, FENETRE),
        Tentatives(f"admin:email:{email}", MAX_ECHECS_EMAIL, FENETRE),
    ]
    if not all([c.essayer() for c in compteurs]):
        journaliser('admin_connexion_echec', request, email=email, bloque=True)
        attente = max(c.attente for c in compteurs)
        reponse = HttpResponse(
            f"Trop de tentatives de connexion. Réessayez dans {attente // 60 + 1} minutes.", status=429,
        )
        reponse['Retry-After'] = str(attente)
        return reponse

    reponse = admin.site.login(request, extra_context)
    if request.user.is_authenticated and request.user.is_staff:
        for c in compteurs:
            c.reussite()
    else:
        journaliser('admin_connexion_echec', request, email=email)
    return reponse
