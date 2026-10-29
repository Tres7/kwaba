from django.urls import path

from .views import ConfigView, ProfilVersementView, RevenusView, WebhookFedaPayView

urlpatterns = [
    path('config/', ConfigView.as_view(), name='paiements-config'),
    path('webhooks/fedapay/', WebhookFedaPayView.as_view(), name='paiements-webhook-fedapay'),
    path('profil-versement/', ProfilVersementView.as_view(), name='paiements-profil-versement'),
    path('revenus/', RevenusView.as_view(), name='paiements-revenus'),
]
