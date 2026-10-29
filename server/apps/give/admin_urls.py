from django.urls import path

from .admin_views import (
    DonsView, OrganisationView, OrganisationsView, ProjetView, ProjetsView, ReversementEffectuerView,
    ReversementsPreparerView, ReversementsView,
)

urlpatterns = [
    path('give/organisations/', OrganisationsView.as_view(), name='admin-give-organisations'),
    path('give/organisations/<uuid:pk>/', OrganisationView.as_view(), name='admin-give-organisation'),
    path('give/organisations/<uuid:pk>/projets/', ProjetsView.as_view(), name='admin-give-projets'),
    path('give/projets/<uuid:pk>/', ProjetView.as_view(), name='admin-give-projet'),
    path('give/reversements/', ReversementsView.as_view(), name='admin-give-reversements'),
    path('give/reversements/preparer/', ReversementsPreparerView.as_view(), name='admin-give-preparer'),
    path('give/reversements/<uuid:pk>/effectuer/', ReversementEffectuerView.as_view(), name='admin-give-effectuer'),
    path('give/dons/', DonsView.as_view(), name='admin-give-dons'),
]
