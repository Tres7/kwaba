from django.urls import path

from .views import VerifierView

urlpatterns = [
    path('verifier/', VerifierView.as_view(), name='correcteur-verifier'),
]
