from django.urls import path

from . import views

urlpatterns = [
    path('', views.VoyagesView.as_view(), name='voyages'),
    path('invitations/<str:code>/', views.InvitationView.as_view(), name='voyage-invitation'),
    path('<uuid:pk>/', views.VoyageView.as_view(), name='voyage'),
    path('<uuid:pk>/nouveau-lien/', views.NouveauLienView.as_view(), name='voyage-nouveau-lien'),
    path('<uuid:pk>/membres/<uuid:user_id>/', views.MembreView.as_view(), name='voyage-membre'),
    path('<uuid:pk>/propositions/', views.PropositionsView.as_view(), name='voyage-propositions'),
    path('<uuid:pk>/propositions/<int:proposition_id>/', views.PropositionView.as_view(), name='voyage-proposition'),
    path('<uuid:pk>/vote/', views.VoteView.as_view(), name='voyage-vote'),
    path('<uuid:pk>/retenir/', views.RetenirView.as_view(), name='voyage-retenir'),
    path('<uuid:pk>/etapes/', views.EtapesView.as_view(), name='voyage-etapes'),
    path('<uuid:pk>/etapes/<int:etape_id>/', views.EtapeView.as_view(), name='voyage-etape'),
    path('<uuid:pk>/reservations/', views.ReservationsPartageesView.as_view(), name='voyage-reservations'),
    path('<uuid:pk>/reservations/<int:lien_id>/', views.ReservationPartageeView.as_view(), name='voyage-reservation'),
    # Payment by a third party: a member pays the booking in the booker's place
    path('<uuid:pk>/reservations/<int:lien_id>/demande-paiement/', views.DemandePaiementGroupeView.as_view(),
         name='voyage-reservation-demande-paiement'),
    path('<uuid:pk>/reservations/<int:lien_id>/paiement/', views.PaiementGroupeView.as_view(),
         name='voyage-reservation-paiement'),
]
