"""
Django settings for atmo project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os

try:
    import urlparse as parse
except ImportError:
    from urllib import parse

import dj_database_url
from decouple import Csv, config


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ROOT = os.path.dirname(os.path.join(BASE_DIR, '..'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# Application definition

INSTALLED_APPS = [
    # Project specific apps
    'atmo',
    'atmo.clusters',
    'atmo.jobs',
    'atmo.workers',

    # Third party apps
    'whitenoise.runserver_nostatic',
    'django_rq',

    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_browserid',
]

for app in config('EXTRA_APPS', default='', cast=Csv()):
    INSTALLED_APPS.append(app)


MIDDLEWARE_CLASSES = (
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'session_csrf.CsrfMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'csp.middleware.CSPMiddleware',
)

ROOT_URLCONF = 'atmo.urls'

WSGI_APPLICATION = 'atmo.wsgi.application'

# AWS configuration
AWS_CONFIG = {
    # AWS EC2 configuration
    'AWS_REGION':             'us-west-2',
    'INSTANCE_TYPE':          'c3.4xlarge',
    'WORKER_AMI':             'ami-0057b733',  # -> telemetry-worker-hvm-20151019 (Ubuntu 15.04)
    'WORKER_PRIVATE_PROFILE': 'telemetry-example-profile',
    'WORKER_PUBLIC_PROFILE':  'telemetry-example-profile',

    # EMR configuration
    # Master and slave instance types should be the same as the telemetry
    # setup bootstrap action depends on it to autotune the cluster.
    'MASTER_INSTANCE_TYPE':   'c3.4xlarge',
    'SLAVE_INSTANCE_TYPE':    'c3.4xlarge',
    'EMR_RELEASE':            'emr-4.3.0',
    'SPARK_INSTANCE_PROFILE': 'telemetry-spark-cloudformation-'
                              'TelemetrySparkInstanceProfile-1SATUBVEXG7E3',
    'SPARK_EMR_BUCKET':       'telemetry-spark-emr-2',

    # Make sure the ephemeral map matches the instance type above.
    'EPHEMERAL_MAP':    {"/dev/xvdb": "ephemeral0", "/dev/xvdc": "ephemeral1"},
    'SECURITY_GROUPS':  [],
    'INSTANCE_PROFILE': 'telemetry-analysis-profile',
    'INSTANCE_APP_TAG': 'telemetry-analysis-worker-instance',
    'EMAIL_SOURCE':     'telemetry-alerts@mozilla.com',

    # Buckets for storing S3 data
    'CODE_BUCKET':         'telemetry-analysis-code-2',
    'PUBLIC_DATA_BUCKET':  'telemetry-public-analysis-2',
    'PRIVATE_DATA_BUCKET': 'telemetry-private-analysis-2',
}

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': config(
        'DATABASE_URL',
        cast=dj_database_url.parse
    )
}

REDIS_URL = config(
    'REDIS_URL',
    cast=parse.urlparse
)

RQ_QUEUES = {
    'default': {
        'HOST': REDIS_URL.hostname,
        'PORT': REDIS_URL.port,
        'DB': 0,
        'PASSWORD': REDIS_URL.password,
        'DEFAULT_TIMEOUT': 600,
    }
}

# Add the django_browserid authentication backend.
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'atmo.utils.auth.AllowMozillaEmailsBackend',
)
LOGIN_URL = "/login/"

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
LANGUAGE_CODE = config('LANGUAGE_CODE', default='en-us')
TIME_ZONE = config('TIME_ZONE', default='UTC')
USE_I18N = config('USE_I18N', default=True, cast=bool)
USE_L10N = config('USE_L10N', default=True, cast=bool)
USE_TZ = config('USE_TZ', default=True, cast=bool)

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_ROOT = config('MEDIA_ROOT', default=os.path.join(BASE_DIR, 'media'))
MEDIA_URL = config('MEDIA_URL', '/media/')

SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=not DEBUG, cast=bool)
SECURE_SSL_REDIRECT = True

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'session_csrf.context_processor',
                'atmo.utils.context_processors.settings',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        }
    },
]
if not DEBUG:
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', TEMPLATES[0]['OPTIONS']['loaders']),
    ]

# Django-CSP
CSP_DEFAULT_SRC = (
    "'self'",
    'https://login.persona.org',
)
CSP_FONT_SRC = (
    "'self'",
    "'unsafe-inline'",
    'http://*.mozilla.net',
    'https://*.mozilla.net',
    'http://*.mozilla.org',
    'https://*.mozilla.org',
    'https://login.persona.org',
)
CSP_IMG_SRC = (
    "'self'",
    "data:",
    'http://*.mozilla.net',
    'https://*.mozilla.net',
    'http://*.mozilla.org',
    'https://*.mozilla.org',
    'https://login.persona.org',
)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    'http://*.mozilla.org',
    'https://*.mozilla.org',
    'http://*.mozilla.net',
    'https://*.mozilla.net',
    'https://login.persona.org',
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    'http://*.mozilla.org',
    'https://*.mozilla.org',
    'http://*.mozilla.net',
    'https://*.mozilla.net',
    'https://login.persona.org',
)

# This is needed to get a CRSF token in /admin
ANON_ALWAYS = True
