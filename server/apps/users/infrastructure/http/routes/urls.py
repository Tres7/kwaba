from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView
from apps.users.infrastructure.http.controllers.AuthController import (
    CaptchaView, RegisterView, LoginView, GoogleAuthView, VerifyEmailView, ResendCodeView,
    PasswordResetRequestView, PasswordResetConfirmView, RefreshView,
)
from apps.users.infrastructure.http.controllers.UserController import MeView

urlpatterns = [
    path('auth/register/',    RegisterView.as_view(),    name='auth-register'),
    path('auth/captcha/',     CaptchaView.as_view(),     name='auth-captcha'),
    path('auth/login/',       LoginView.as_view(),       name='auth-login'),
    path('auth/refresh/',     RefreshView.as_view(),     name='token-refresh'),
    path('auth/logout/',      TokenBlacklistView.as_view(), name='auth-logout'),
    path('auth/verify/',      VerifyEmailView.as_view(), name='auth-verify'),
    path('auth/resend-code/', ResendCodeView.as_view(),  name='auth-resend-code'),
    path('users/me/',         MeView.as_view(),          name='user-me'),
    path('auth/google/',      GoogleAuthView.as_view(),  name='auth-google'),
    path('auth/password-reset/',         PasswordResetRequestView.as_view(), name='auth-password-reset'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
]



