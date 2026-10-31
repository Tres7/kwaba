"""
Django settings for Kwa-Ba project.
"""

import hashlib
import hmac
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from config.storage import r2_storage, r2_storage_prive

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

def _env_bool(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() in ('true', '1', 'yes')


def _env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]


# Production by default: development enables DEBUG explicitly (server/.env)
DEBUG = _env_bool('DJANGO_DEBUG', 'False')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY est obligatoire hors développement (DJANGO_DEBUG=False).')
    SECRET_KEY = 'django-insecure-dev-only'

ALLOWED_HOSTS = _env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,backend')
# Render provides the public host name of the service
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    # Local
    'apps.users',
    'apps.notifications.apps.NotificationsConfig',
    'apps.hebergements.apps.HebergementsConfig',
    'apps.reservations.apps.ReservationsConfig',
    'apps.favoris.apps.FavorisConfig',
    'apps.avis.apps.AvisConfig',
    'apps.messaging.apps.MessagingConfig',
    'apps.paiements.apps.PaiementsConfig',
    'apps.transferts.apps.TransfertsConfig',
    'apps.voyages.apps.VoyagesConfig',
    'apps.concierge.apps.ConciergeConfig',
    'apps.give.apps.GiveConfig',
    'apps.securite.apps.SecuriteConfig',
    'apps.verifications.apps.VerificationsConfig',
    'apps.locations.apps.LocationsConfig',
    'apps.documents.apps.DocumentsConfig',
    'apps.contrats.apps.ContratsConfig',
    'apps.experiences.apps.ExperiencesConfig',
    'apps.terrain.apps.TerrainConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Static files (admin) served by the application, without a web server in front of Gunicorn
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database - PostgreSQL via Docker

# No default password outside development: a forgotten variable must not open the database
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
if not POSTGRES_PASSWORD:
    if not DEBUG:
        raise ImproperlyConfigured('POSTGRES_PASSWORD est obligatoire hors développement (DJANGO_DEBUG=False).')
    POSTGRES_PASSWORD = 'kwaba'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'kwaba'),
        'USER': os.getenv('POSTGRES_USER', 'kwaba'),
        'PASSWORD': POSTGRES_PASSWORD,
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'

# Photos and avatars: local disk in development, Cloudflare R2 object storage (S3 API) as soon as R2_BUCKET
# is set. The disk of Render containers is ephemeral: without R2, photos disappear at redeploy.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
if (_r2 := r2_storage(os.environ)) is not None:
    STORAGES['default'] = _r2

# Private documents (hosts' identity documents, photos of verification visits): never served directly,
# only read by the API after checking the role. Private R2 bucket in production, otherwise a folder outside MEDIA_ROOT.
PRIVE_ROOT = Path(os.getenv('PRIVE_ROOT', BASE_DIR / 'prive'))
STORAGES['prive'] = r2_storage_prive(os.environ) or {
    'BACKEND': 'django.core.files.storage.FileSystemStorage',
    'OPTIONS': {'location': PRIVE_ROOT, 'base_url': None},
}


# Default primary key field type

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.UserModel'


# Django REST Framework

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'COERCE_DECIMAL_TO_STRING': False,
    # Throttles per scope (applied only to the views that declare them)
    # Client address behind the trusted proxies (see NUM_PROXIES): used by the DRF throttles
    'NUM_PROXIES': None,
    'DEFAULT_THROTTLE_RATES': {
        'messaging_conversation_create': '10/hour',
        'messaging_message_send': '30/min',
        'hebergement_photo_upload': '120/hour',
        'concierge_conversation': '30/hour',
        'verification_piece': '20/hour',
        'reclamation': '5/hour',
    },
}

# Number of trusted proxies in front of the API (Render, nginx…): the client address is the one added by the
# last of them in X-Forwarded-For. 0: address of the connection (an X-Forwarded-For sent by the client is
# ignored, so it cannot get around the rate limits).
NUM_PROXIES = int(os.getenv('DJANGO_NUM_PROXIES', '0'))
REST_FRAMEWORK['NUM_PROXIES'] = NUM_PROXIES

# Absolute addresses (uploaded photos) use the public host, not the internal name of the API: the Next.js proxy and
# nginx both set this header, and nginx replaces whatever a visitor sends. ALLOWED_HOSTS still applies to it.
USE_X_FORWARDED_HOST = True

# Rate and attempt limits (sign-in, sign-up, codes, administration…). Can be disabled for a load test
# only; always active in production.
LIMITES_ACTIVES = _env_bool('LIMITES_ACTIVES', 'True')


# Cache shared between processes (throttle counters), stored in PostgreSQL.
# The table is created by the messaging 0002 migration (createcachetable).

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
    }
}


# Messagerie (voir documentation/modules/messaging.md)

MESSAGING = {
    'EMAIL_DELAY_SECONDS': int(os.getenv('MESSAGING_EMAIL_DELAY_SECONDS', '60')),
    'EMAIL_HOURLY_CAP': int(os.getenv('MESSAGING_EMAIL_HOURLY_CAP', '5')),
    'OUTBOX_RETENTION_DAYS': int(os.getenv('MESSAGING_OUTBOX_RETENTION_DAYS', '7')),
    'RELAY_INTERVAL_SECONDS': int(os.getenv('MESSAGING_RELAY_INTERVAL_SECONDS', '10')),
}

# Online payment (FedaPay). Without a FedaPay or PayPal key, online payment is disabled:
# bookings are then confirmed immediately, without collecting money.
FEDAPAY = {
    'SECRET_KEY': os.getenv('FEDAPAY_SECRET_KEY', ''),
    'ENV': os.getenv('FEDAPAY_ENV', 'sandbox'),  # sandbox | live
    # Required outside development: without it, webhooks are refused (see paiements.views)
    'WEBHOOK_SECRET': os.getenv('FEDAPAY_WEBHOOK_SECRET', ''),
    # Time during which the dates stay held while waiting for the payment
    'EXPIRATION_MINUTES': int(os.getenv('PAIEMENT_EXPIRATION_MINUTES', '30')),
}

# Without FedaPay or PayPal configured, a booking can only be confirmed without payment in development:
# in production, it is refused ("payment temporarily unavailable") instead of being confirmed for free.
PAIEMENT_HORS_LIGNE = _env_bool('PAIEMENT_HORS_LIGNE', str(DEBUG))

# Pre-launch mode: listings hidden from the public, no booking or payment until the opening (config/prelancement.py)
PRELANCEMENT = _env_bool('PRELANCEMENT', 'False')

# PayPal (payment in euros). Without credentials, PayPal is not offered.
# Payouts to hosts always go through FedaPay.
PAYPAL = {
    'CLIENT_ID': os.getenv('PAYPAL_CLIENT_ID', ''),
    'CLIENT_SECRET': os.getenv('PAYPAL_CLIENT_SECRET', ''),
    'ENV': os.getenv('PAYPAL_ENV', 'sandbox'),  # sandbox | live
}

# Frontend URL, used in the email links
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
# Pause between two emails sent by the payments worker (limit of test SMTPs like Mailtrap)
PAIEMENTS_PAUSE_EMAIL = float(os.getenv('PAIEMENTS_PAUSE_EMAIL', '1'))

# AI Concierge (Gemini, Google's Interactions API). Without a key, the Concierge is disabled.
CONCIERGE = {
    'API_KEY': os.getenv('GEMINI_API_KEY', ''),
    'MODELE': os.getenv('CONCIERGE_MODELE', 'gemini-3.8-flash'),
    # Model thinking depth: minimal | low | medium | high (low = fast answers)
    'REFLEXION': os.getenv('CONCIERGE_REFLEXION', 'low'),
    'RECHERCHE_WEB': os.getenv('CONCIERGE_RECHERCHE_WEB', 'True').lower() in ('true', '1', 'yes'),
    # Limits per user (API cost)
    'MAX_PAR_HEURE': int(os.getenv('CONCIERGE_MAX_PAR_HEURE', '20')),
    'MAX_PAR_JOUR': int(os.getenv('CONCIERGE_MAX_PAR_JOUR', '60')),
}

# Support contact given to travellers (airport transfers…)
ASSISTANCE_CONTACT = os.getenv('ASSISTANCE_CONTACT', 'info@kwa-ba.com')

# Module switches (config/site.py): hidden at launch. To switch one back on, set its MODULE_… variable
# to True in the API environment and restart the API: no code deployment is needed.
MODULES = {nom: _env_bool(f'MODULE_{nom.upper()}', 'False') for nom in (
    'experiences', 'together', 'give', 'concierge', 'location_sans_chauffeur', 'paiements_non_ouverts',
)}

# Legal notices expected after registration (empty: "to be completed" on the site). The RCCM and NIF
# entered in the back-office (Documents → Company information) are used while these variables are empty.
def _mention(nom: str) -> str:
    # A comment left on the line of an empty variable ("SOCIETE_NIF=   # …") may be read as its value:
    # it then counts as empty ("to be completed"), never displayed as is
    valeur = os.getenv(nom, '').strip()
    return '' if valeur.startswith('#') else valeur


MENTIONS_LEGALES = {
    'rccm': _mention('SOCIETE_RCCM'),
    'nif': _mention('SOCIETE_NIF'),
    'commerce_electronique': _mention('SOCIETE_COMMERCE_ELECTRONIQUE'),  # decree no. 2018-062/PR
    'ipdcp': _mention('SOCIETE_IPDCP'),  # declaration to the IPDCP
}
# Company not registered yet: "SAS en formation" on the site, until the RCCM
SOCIETE_EN_FORMATION = _env_bool('SOCIETE_EN_FORMATION', 'True')

# Google Analytics measurement ID (G-…). Empty: no audience measurement and no cookie banner (config/site.py)
GOOGLE_ANALYTICS_ID = _mention('GOOGLE_ANALYTICS_ID')

# Reply-to address of the sent emails (users' replies arrive in this mailbox)
EMAIL_REPLY_TO = os.getenv('EMAIL_REPLY_TO', '')

# Public URL of the API (links to the administration in the alerts)
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')

# Hosts displayed images may come from (avatars, listing photos): the API itself (uploaded photos),
# the R2 public domain, Google avatars and the demo photos. A host starting with a dot
# covers its subdomains. IMAGES_HOTES adds hosts (separated by commas), to add as well to img-src in
# client/next.config.ts: the browser refuses any other host.
IMAGES_HOTES_AUTORISES = [
    h for h in {
        urlsplit(BACKEND_URL).hostname,
        os.getenv('R2_PUBLIC_DOMAIN', '').strip().lower() or None,
        os.getenv('RENDER_EXTERNAL_HOSTNAME') or None,
        '.googleusercontent.com',
        'images.unsplash.com',
        *_env_list('IMAGES_HOTES', ''),
        *(['localhost', '127.0.0.1', 'backend'] if DEBUG else []),
    } if h
]


# HTTPS in production: Render terminates TLS and passes X-Forwarded-Proto
SECURE_REDIRECT_EXEMPT = [r'^api/health/$']   # internal health probe, over HTTP
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = _env_bool('DJANGO_SECURE_SSL_REDIRECT', 'True')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', str(60 * 60 * 24 * 365)))

# The API is served on a subdomain (onrender.com, then a team domain): HSTS must neither cover
# the other subdomains nor be preloaded in browsers, decisions to make at the domain level.
SILENCED_SYSTEM_CHECKS = ['security.W005', 'security.W021']


# CORS

CORS_ALLOWED_ORIGINS = _env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
# Name of the downloaded PDFs (vouchers, receipts, invoices), read by the site
CORS_EXPOSE_HEADERS = ['Content-Disposition']


# JWT signing key separate from SECRET_KEY (administration sessions, Django signatures):
# JWT_SIGNING_KEY if provided, otherwise a key derived from SECRET_KEY, specific to this use.
JWT_SIGNING_KEY = os.getenv('JWT_SIGNING_KEY') or hmac.new(
    SECRET_KEY.encode(), b'kwaba-jwt-signing-key', hashlib.sha256,
).hexdigest()

SIMPLE_JWT = {
    'SIGNING_KEY': JWT_SIGNING_KEY,
    # Short lifetime: NextAuth renews the access token automatically; a stolen token is useful for a short time
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    # Each renewal (rotation) starts again for this duration. The site session itself closes 5 min after
    # leaving the site (NextAuth session.maxAge, client/src/auth.ts): the refresh token is no longer
    # usable afterwards, this duration only bounds a token that would have leaked
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', '1'))),
    'ROTATE_REFRESH_TOKENS': True,
    # The old refresh token is blacklisted at every rotation (cleanup: manage.py flushexpiredtokens)
    'BLACKLIST_AFTER_ROTATION': True,
    # Tokens carry a fingerprint of the password: changing it invalidates every access token issued before
    'CHECK_REVOKE_TOKEN': True,
}

# Google sign-in: Kwa-Ba's OAuth client ID(s) (separated by commas). A Google token issued for another
# application is refused; without a configured ID, Google sign-in is disabled.
GOOGLE_CLIENT_IDS = _env_list('GOOGLE_CLIENT_ID', '')

# Cloudflare Turnstile captcha at sign-in and sign-up ("I am human" box). Keys created in the
# Cloudflare dashboard (Turnstile), without hosting the domain at Cloudflare. Without a secret key: disabled.
TURNSTILE_SITE_KEY = os.getenv('TURNSTILE_SITE_KEY', '')
TURNSTILE_SECRET_KEY = os.getenv('TURNSTILE_SECRET_KEY', '')

# Delay during which a refresh token that was just renewed still returns the same new pair.
# NextAuth renews the same token in parallel when a page loads: without this delay, only the first
# call would succeed and the others would sign the user out.
JWT_REFRESH_GRACE_SECONDS = int(os.getenv('JWT_REFRESH_GRACE_SECONDS', '60'))

# Email (so the provider can be changed at any time)
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() in ("true", "1", "yes")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))


# Recipients of the error alerts (ADMINS="Name <email>, ..." or emails separated by commas)
ADMINS = [('', email) for email in _env_list('ADMINS', '')]

# Django administration: configurable path (avoids the bots targeting /admin/)
ADMIN_URL = os.getenv('DJANGO_ADMIN_URL', 'admin/').strip('/') + '/'

# Logging: shows the INFO logs of the business modules (apps.*) in the container output
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{levelname}] {name}: {message}', 'style': '{'},
    },
    'filters': {
        'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'},
        'sans_sonde_de_sante': {'()': 'config.log_filters.SansSondeDeSante'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
        # 500 errors emailed to the ADMINS (production only), without the local variables
        'mail_admins': {
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false', 'sans_sonde_de_sante'],
            'include_html': False,
        },
    },
    'loggers': {
        'apps': {'handlers': ['console'], 'level': 'INFO'},
        'django.request': {'handlers': ['console', 'mail_admins'], 'level': 'ERROR', 'propagate': False},
        'django.security': {'handlers': ['console', 'mail_admins'], 'level': 'WARNING', 'propagate': False},
    },
}

