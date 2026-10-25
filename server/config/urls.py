"""
URL configuration for Kwa-Ba project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.securite.admin_site import connexion_admin
from config.health import health
from config.reclamation import ReclamationView
from config.site import site

urlpatterns = [
    # Avant admin.site.urls : la page de connexion de l'administration limite les tentatives
    path(f'{settings.ADMIN_URL}login/', connexion_admin),
    path(settings.ADMIN_URL, admin.site.urls),
    path('api/health/', health, name='health'),
    path('api/v1/site/', site, name='site'),
    path('api/v1/site/reclamation/', ReclamationView.as_view(), name='reclamation'),
    path('api/v1/', include('apps.users.infrastructure.http.routes.urls')),
    path('api/v1/hebergements/', include('apps.hebergements.urls')),
    path('api/v1/reservations/', include('apps.reservations.urls')),
    path('api/v1/favoris/', include('apps.favoris.urls')),
    path('api/v1/avis/', include('apps.avis.urls')),
    path('api/v1/paiements/', include('apps.paiements.urls')),
    path('api/v1/transferts/', include('apps.transferts.urls')),
    path('api/v1/voyages/', include('apps.voyages.urls')),
    path('api/v1/concierge/', include('apps.concierge.urls')),
    path('api/v1/give/', include('apps.give.urls')),
    path('api/v1/verifications/', include('apps.verifications.urls')),
    path('api/v1/agent/', include('apps.terrain.urls')),
    path('api/v1/locations/', include('apps.locations.urls')),
    path('api/v1/experiences/', include('apps.experiences.urls')),
    path('api/v1/admin/documents/', include('apps.documents.admin_urls')),
    path('api/v1/admin/contrats/', include('apps.contrats.admin_urls')),
    path('api/v1/admin/', include('apps.backoffice.urls')),
    path('api/v1/documents/', include('apps.documents.urls')),
    path('api/v1/contrats/', include('apps.contrats.urls')),
    path('api/v1/messaging/', include('apps.messaging.infrastructure.http.routes.urls')),
]

# Photos envoyées par les hôtes (en production, servies par le serveur web / un stockage objet)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
