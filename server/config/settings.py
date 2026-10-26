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


# Production par défaut : le développement active DEBUG explicitement (server/.env)
DEBUG = _env_bool('DJANGO_DEBUG', 'False')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY est obligatoire hors développement (DJANGO_DEBUG=False).')
    SECRET_KEY = 'django-insecure-dev-only'

ALLOWED_HOSTS = _env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,backend')
# Render fournit le nom d'hôte public du service
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
    # Fichiers statiques (admin) servis par l'application, sans serveur web devant Gunicorn
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

# Pas de mot de passe par défaut hors développement : une variable oubliée ne doit pas ouvrir la base
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

# Photos et avatars : disque local en développement, stockage objet Cloudflare R2 (API S3) dès que R2_BUCKET
# est défini. Le disque des conteneurs Render est éphémère : sans R2, les photos disparaissent au redéploiement.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
if (_r2 := r2_storage(os.environ)) is not None:
    STORAGES['default'] = _r2

# Documents privés (pièces d'identité des hôtes, photos des visites de vérification) : jamais servis directement,
# lus seulement par l'API après contrôle du rôle. Bucket R2 privé en production, sinon un dossier hors MEDIA_ROOT.
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
    # Throttles par scope (appliqués uniquement aux vues qui les déclarent)
    # Adresse du client derrière les proxys de confiance (voir NUM_PROXIES) : utilisée par les throttles DRF
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

# Nombre de proxys de confiance devant l'API (Render, nginx…) : l'adresse du client est celle ajoutée par le
# dernier d'entre eux dans X-Forwarded-For. 0 : adresse de la connexion (un X-Forwarded-For envoyé par le client
# est ignoré, il ne peut donc pas contourner les limites de débit).
NUM_PROXIES = int(os.getenv('DJANGO_NUM_PROXIES', '0'))
REST_FRAMEWORK['NUM_PROXIES'] = NUM_PROXIES

# Limites de débit et de tentatives (connexion, inscription, codes, administration…). Désactivables pour un test
# de charge uniquement ; toujours actives en production.
LIMITES_ACTIVES = _env_bool('LIMITES_ACTIVES', 'True')


# Cache partagé entre processus (compteurs des throttles), stocké dans PostgreSQL.
# La table est créée par la migration messaging 0002 (createcachetable).

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

# Paiement en ligne (FedaPay). Sans clé FedaPay ni PayPal, le paiement en ligne est désactivé :
# les réservations sont alors confirmées immédiatement, sans encaissement.
FEDAPAY = {
    'SECRET_KEY': os.getenv('FEDAPAY_SECRET_KEY', ''),
    'ENV': os.getenv('FEDAPAY_ENV', 'sandbox'),  # sandbox | live
    # Obligatoire hors développement : sans elle, les webhooks sont refusés (voir paiements.views)
    'WEBHOOK_SECRET': os.getenv('FEDAPAY_WEBHOOK_SECRET', ''),
    # Durée pendant laquelle les dates restent bloquées en attendant le paiement
    'EXPIRATION_MINUTES': int(os.getenv('PAIEMENT_EXPIRATION_MINUTES', '30')),
}

# Sans FedaPay ni PayPal configuré, une réservation ne peut être confirmée sans paiement qu'en développement :
# en production, elle est refusée (« paiement momentanément indisponible ») au lieu d'être confirmée gratuitement.
PAIEMENT_HORS_LIGNE = _env_bool('PAIEMENT_HORS_LIGNE', str(DEBUG))

# Pre-launch mode: listings hidden from the public, no booking or payment until the opening (config/prelancement.py)
PRELANCEMENT = _env_bool('PRELANCEMENT', 'False')

# PayPal (paiement en euros). Sans identifiants, PayPal n'est pas proposé.
# Les versements aux hôtes passent toujours par FedaPay.
PAYPAL = {
    'CLIENT_ID': os.getenv('PAYPAL_CLIENT_ID', ''),
    'CLIENT_SECRET': os.getenv('PAYPAL_CLIENT_SECRET', ''),
    'ENV': os.getenv('PAYPAL_ENV', 'sandbox'),  # sandbox | live
}

# URL du frontend, utilisée dans les liens des emails
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
# Pause entre deux emails envoyés par le worker des paiements (limite des SMTP de test comme Mailtrap)
PAIEMENTS_PAUSE_EMAIL = float(os.getenv('PAIEMENTS_PAUSE_EMAIL', '1'))

# AI Concierge (Gemini, API Interactions de Google). Sans clé, le Concierge est désactivé.
CONCIERGE = {
    'API_KEY': os.getenv('GEMINI_API_KEY', ''),
    'MODELE': os.getenv('CONCIERGE_MODELE', 'gemini-3.8-flash'),
    # Profondeur de réflexion du modèle : minimal | low | medium | high (low = réponses rapides)
    'REFLEXION': os.getenv('CONCIERGE_REFLEXION', 'low'),
    'RECHERCHE_WEB': os.getenv('CONCIERGE_RECHERCHE_WEB', 'True').lower() in ('true', '1', 'yes'),
    # Limites par utilisateur (coût de l'API)
    'MAX_PAR_HEURE': int(os.getenv('CONCIERGE_MAX_PAR_HEURE', '20')),
    'MAX_PAR_JOUR': int(os.getenv('CONCIERGE_MAX_PAR_JOUR', '60')),
}

# Contact d'assistance donné aux voyageurs (transferts aéroport…)
ASSISTANCE_CONTACT = os.getenv('ASSISTANCE_CONTACT', 'info@kwa-ba.com')

# Interrupteurs des modules (config/site.py) : masqués au lancement. Pour en rallumer un, passer sa variable
# MODULE_… à True dans l'environnement de l'API et redémarrer l'API : aucun déploiement de code n'est nécessaire.
MODULES = {nom: _env_bool(f'MODULE_{nom.upper()}', 'False') for nom in (
    'experiences', 'together', 'give', 'concierge', 'location_sans_chauffeur', 'paiements_non_ouverts',
)}

# Mentions légales attendues après l'immatriculation (vides : « à compléter » sur le site). Le RCCM et le NIF
# saisis dans le back-office (Documents → Informations société) servent tant que ces variables sont vides.
def _mention(nom: str) -> str:
    # Un commentaire laissé sur la ligne d'une variable vide (« SOCIETE_NIF=   # … ») peut être lu comme sa valeur :
    # il compte alors comme vide (« à compléter »), jamais affiché tel quel
    valeur = os.getenv(nom, '').strip()
    return '' if valeur.startswith('#') else valeur


MENTIONS_LEGALES = {
    'rccm': _mention('SOCIETE_RCCM'),
    'nif': _mention('SOCIETE_NIF'),
    'commerce_electronique': _mention('SOCIETE_COMMERCE_ELECTRONIQUE'),  # décret n° 2018-062/PR
    'ipdcp': _mention('SOCIETE_IPDCP'),  # déclaration auprès de l'IPDCP
}

# Adresse de réponse des emails envoyés (les réponses des utilisateurs arrivent dans cette boîte)
EMAIL_REPLY_TO = os.getenv('EMAIL_REPLY_TO', '')

# URL publique de l'API (liens vers l'administration dans les alertes)
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')

# Hôtes d'où peuvent venir les images affichées (avatars, photos d'annonces) : l'API elle-même (photos envoyées),
# le domaine public R2, les avatars Google et les photos de démonstration. Un hôte commençant par un point
# couvre ses sous-domaines. IMAGES_HOTES ajoute des hôtes (séparés par des virgules).
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


# HTTPS en production : Render termine TLS et transmet X-Forwarded-Proto
SECURE_REDIRECT_EXEMPT = [r'^api/health/$']   # sonde de santé interne, en HTTP
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

# L'API est servie sur un sous-domaine (onrender.com, puis un domaine de l'équipe) : HSTS ne doit ni couvrir
# les autres sous-domaines ni être préchargé dans les navigateurs, décisions à prendre au niveau du domaine.
SILENCED_SYSTEM_CHECKS = ['security.W005', 'security.W021']


# CORS

CORS_ALLOWED_ORIGINS = _env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
# Nom des PDF téléchargés (bons, reçus, factures), lu par le site
CORS_EXPOSE_HEADERS = ['Content-Disposition']


# Clé de signature des JWT distincte de SECRET_KEY (sessions de l'administration, signatures Django) :
# JWT_SIGNING_KEY si elle est fournie, sinon une clé dérivée de SECRET_KEY, propre à cet usage.
JWT_SIGNING_KEY = os.getenv('JWT_SIGNING_KEY') or hmac.new(
    SECRET_KEY.encode(), b'kwaba-jwt-signing-key', hashlib.sha256,
).hexdigest()

SIMPLE_JWT = {
    'SIGNING_KEY': JWT_SIGNING_KEY,
    # Courte durée : NextAuth renouvelle le jeton d'accès automatiquement ; un jeton volé sert peu de temps
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    # Chaque renouvellement (rotation) repart pour cette durée. La session du site, elle, se ferme 5 min après
    # avoir quitté le site (session.maxAge de NextAuth, client/src/auth.ts) : le refresh token n'est plus
    # utilisable ensuite, cette durée ne fait que borner un jeton qui aurait fuité
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', '1'))),
    'ROTATE_REFRESH_TOKENS': True,
    # L'ancien refresh token est mis sur liste noire à chaque rotation (purge : manage.py flushexpiredtokens)
    'BLACKLIST_AFTER_ROTATION': True,
    # Les jetons portent une empreinte du mot de passe : en changer invalide tous les jetons d'accès émis avant
    'CHECK_REVOKE_TOKEN': True,
}

# Connexion Google : identifiant(s) OAuth de Kwa-Ba (séparés par des virgules). Un jeton Google émis pour une autre
# application est refusé ; sans identifiant configuré, la connexion Google est désactivée.
GOOGLE_CLIENT_IDS = _env_list('GOOGLE_CLIENT_ID', '')

# Captcha Cloudflare Turnstile à la connexion et à l'inscription (case « Je suis humain »). Clés créées dans le
# tableau de bord Cloudflare (Turnstile), sans héberger le domaine chez Cloudflare. Sans clé secrète : désactivé.
TURNSTILE_SITE_KEY = os.getenv('TURNSTILE_SITE_KEY', '')
TURNSTILE_SECRET_KEY = os.getenv('TURNSTILE_SECRET_KEY', '')

# Délai pendant lequel un refresh token qui vient d'être renouvelé renvoie encore la même nouvelle paire.
# NextAuth renouvelle le même jeton en parallèle au chargement d'une page : sans ce délai, seul le premier
# appel réussirait et les autres déconnecteraient l'utilisateur.
JWT_REFRESH_GRACE_SECONDS = int(os.getenv('JWT_REFRESH_GRACE_SECONDS', '60'))

# Email (permet donc de changer de provider quand on veut)
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


# Destinataires des alertes d'erreur (ADMINS=« Nom <email>, ... » ou emails séparés par des virgules)
ADMINS = [('', email) for email in _env_list('ADMINS', '')]

# Administration Django : chemin configurable (évite les robots qui visent /admin/)
ADMIN_URL = os.getenv('DJANGO_ADMIN_URL', 'admin/').strip('/') + '/'

# Logging : affiche les logs INFO des modules métier (apps.*) dans la sortie des conteneurs
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
        # Erreurs 500 envoyées par email aux ADMINS (production uniquement), sans les variables locales
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

