import os
import sys
from pathlib import Path
from datetime import timedelta
import dotenv

# Load environment variables
dotenv.load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Core Security & Secrets Configuration
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', os.environ.get('SECRET_KEY'))
if not SECRET_KEY:
    if DEBUG or any(arg in sys.argv for arg in ['test', 'pytest', 'makemigrations', 'migrate', 'collectstatic']):
        SECRET_KEY = 'django-insecure-dev-fallback-key-for-local-testing-only'
    else:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("DJANGO_SECRET_KEY environment variable must be set in production.")

# Host Header Validation
ALLOWED_HOSTS_ENV = os.environ.get('ALLOWED_HOSTS', '')
if ALLOWED_HOSTS_ENV:
    ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_ENV.split(',') if h.strip()]
elif DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if RAILWAY_PUBLIC_DOMAIN and RAILWAY_PUBLIC_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

# Production HTTPS / CSRF Configuration for Cloud Platforms
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS_ENV = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if CSRF_TRUSTED_ORIGINS_ENV:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in CSRF_TRUSTED_ORIGINS_ENV.split(',') if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://*.onrender.com',
        'https://*.up.railway.app',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')
if RAILWAY_PUBLIC_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RAILWAY_PUBLIC_DOMAIN}')

# The Fernet key must be kept secret. Losing the key will make encrypted credentials unrecoverable.
FERNET_KEY = os.environ.get('FERNET_KEY')
if not FERNET_KEY:
    if DEBUG or any(arg in sys.argv for arg in ['test', 'pytest', 'makemigrations', 'migrate', 'collectstatic', 'seed_network_demo']):
        # Development and testing fallback key (never use in real production)
        FERNET_KEY = 'W3sO-LqP7b_dG5vUv-0L2Y1t9kLpM_xZ7sQ2dF4jK8M='
    else:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("FERNET_KEY environment variable must be set in production.")

SIMULATOR_MODE = os.environ.get('SIMULATOR_MODE', 'True').lower() in ('true', '1', 't')

import dj_database_url

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party packages
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',

    # NetWatch Application Apps
    'apps.accounts',
    'apps.devices',
    'apps.monitoring',
    'apps.network_engine',
    'apps.automation',
    'apps.alerts',
    'apps.metrics',
    'apps.audit',
    'apps.events',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditLoggingMiddleware',
]

ROOT_URLCONF = 'netwatch_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates', BASE_DIR.parent / 'frontend'],
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

WSGI_APPLICATION = 'netwatch_core.wsgi.application'

# Database Configuration (PostgreSQL with SQLite fallback for local test/dev)
USE_SQLITE = os.environ.get('USE_SQLITE', 'True').lower() in ('true', '1', 't')
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'netwatch_db'),
            'USER': os.environ.get('DB_USER', 'netwatch_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    }

# Static Files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR.parent / 'frontend',
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# MongoDB Telemetry Configuration
MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DB_NAME = os.environ.get('MONGODB_DB_NAME', 'netwatch_telemetry')
MONGODB_ENABLED = os.environ.get('MONGODB_ENABLED', 'False').lower() in ('true', '1', 't')

# Custom Auth User Model
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'EXCEPTION_HANDLER': 'netwatch_core.exceptions.custom_exception_handler',
}

# SimpleJWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = os.environ.get('CORS_ALLOW_ALL_ORIGINS', 'True' if DEBUG else 'False').lower() in ('true', '1', 't')
CORS_ALLOWED_ORIGINS_ENV = os.environ.get('CORS_ALLOWED_ORIGINS', '')
if CORS_ALLOWED_ORIGINS_ENV:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in CORS_ALLOWED_ORIGINS_ENV.split(',') if o.strip()]
CORS_ALLOW_CREDENTIALS = True

# Celery Configuration & Distributed Processing
USE_EAGER_CELERY = any(arg in sys.argv for arg in ['test', 'pytest']) or os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'True').lower() in ('true', '1', 't')

if USE_EAGER_CELERY:
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
else:
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    CELERY_TASK_ALWAYS_EAGER = False

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_WORKER_CONCURRENCY = int(os.environ.get('CELERY_WORKER_CONCURRENCY', 4))
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# Queue Separation & Routing
CELERY_TASK_ROUTES = {
    'apps.monitoring.tasks.poll_device_icmp_task': {'queue': 'high_priority_icmp'},
    'apps.monitoring.tasks.poll_device_snmp_task': {'queue': 'snmp_telemetry'},
    'apps.monitoring.tasks.run_periodic_fleet_polling_task': {'queue': 'default'},
}

# Periodic Celery Beat Scheduling
CELERY_BEAT_SCHEDULE = {
    'poll-fleet-devices-every-30-seconds': {
        'task': 'apps.monitoring.tasks.run_periodic_fleet_polling_task',
        'schedule': 30.0,
    },
}

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'netwatch.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'netwatch': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
