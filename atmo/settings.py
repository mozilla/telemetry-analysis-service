# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
"""
Django settings for atmo project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""
from datetime import timedelta
import os

import dj_database_url
from django.core.urlresolvers import reverse_lazy
from decouple import Csv, config

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

SITE_ID = 1

# The URL under which this instance is running
SITE_URL = config('SITE_URL', default='http://localhost:8000')

# Whether or not this runs in Heroku
IS_HEROKU = 'HEROKU_APP_NAME' in os.environ

# Application definition

INSTALLED_APPS = [
    # Project specific apps
    'atmo',
    'atmo.clusters',
    'atmo.jobs',
    'atmo.users',

    # Third party apps
    'whitenoise.runserver_nostatic',
    'django_rq',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # Django apps
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE_CLASSES = (
    'django.middleware.security.SecurityMiddleware',
    'atmo.middleware.NewRelicPapertrailMiddleware',
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
    'AWS_REGION': 'us-west-2',

    # EMR configuration
    # Master and slave instance types should be the same as the telemetry
    # setup bootstrap action depends on it to autotune the cluster.
    'MASTER_INSTANCE_TYPE': 'c3.4xlarge',
    'WORKER_INSTANCE_TYPE': 'c3.4xlarge',
    'USE_SPOT_INSTANCES': config('USE_SPOT_INSTANCES', default=True, cast=bool),
    'CORE_SPOT_BID': config('CORE_SPOT_BID', default='0.84'),
    'EMR_RELEASE': 'emr-4.3.0',
    'SPARK_INSTANCE_PROFILE': 'telemetry-spark-cloudformation-'
                              'TelemetrySparkInstanceProfile-1SATUBVEXG7E3',
    'SPARK_EMR_BUCKET': 'telemetry-spark-emr-2',
    'INSTANCE_APP_TAG': 'telemetry-analysis-worker-instance',
    'EMAIL_SOURCE': 'telemetry-alerts@mozilla.com',

    # Tags for accounting purposes
    'ACCOUNTING_APP_TAG': 'telemetry-analysis',
    'ACCOUNTING_TYPE_TAG': 'worker',

    # Buckets for storing S3 data
    'CODE_BUCKET': 'telemetry-analysis-code-2',
    'PUBLIC_DATA_BUCKET': 'telemetry-public-analysis-2',
    'PRIVATE_DATA_BUCKET': 'telemetry-private-analysis-2',
}

for aws_cred in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION'):
    if aws_cred not in os.environ:
        os.environ[aws_cred] = config(aws_cred, default='')


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': config(
        'DATABASE_URL',
        cast=dj_database_url.parse
    )
}
# require encrypted connections to Postgres
if IS_HEROKU:
    DATABASES['default'].setdefault('OPTIONS', {})['sslmode'] = 'require'

REDIS_URL = config('REDIS_URL')

RQ_QUEUES = {
    'default': {
        'URL': REDIS_URL,
        'DEFAULT_TIMEOUT': 600,
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Add the django-allauth authentication backend.
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

LOGIN_URL = reverse_lazy('account_login')
LOGOUT_URL = reverse_lazy('account_logout')
LOGIN_REDIRECT_URL = reverse_lazy('dashboard')

# django-allauth configuration
ACCOUNT_LOGOUT_REDIRECT_URL = LOGIN_REDIRECT_URL
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 7
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[Telemetry Analysis Service] '
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'optional'
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_ADAPTER = 'atmo.users.adapters.AtmoAccountAdapter'
ACCOUNT_USERNAME_REQUIRED = False

SOCIALACCOUNT_ADAPTER = 'atmo.users.adapters.AtmoSocialAccountAdapter'
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'  # no extra verification needed
SOCIALACCOUNT_QUERY_EMAIL = True  # needed by the Google provider

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'HOSTED_DOMAIN': 'mozilla.com',
        'AUTH_PARAMS': {
            'prompt': 'select_account',
        }
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
LANGUAGE_CODE = config('LANGUAGE_CODE', default='en-us')
TIME_ZONE = config('TIME_ZONE', default='UTC')
USE_I18N = False
USE_L10N = False
USE_TZ = config('USE_TZ', default=True, cast=bool)
DATETIME_FORMAT = 'Y-m-d H:i'  # simplified ISO format since we assume UTC

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_ROOT = config('MEDIA_ROOT', default=os.path.join(BASE_DIR, 'media'))
MEDIA_URL = config('MEDIA_URL', '/media/')

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
X_FRAME_OPTIONS = 'DENY'

if SITE_URL.startswith('https://'):
    ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = int(timedelta(days=365).total_seconds())
    # Mark session and CSRF cookies as being HTTPS-only.
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True


SILENCED_SYSTEM_CHECKS = [
    'security.W003',  # We're using django-session-csrf
    # We can't set SECURE_HSTS_INCLUDE_SUBDOMAINS since this runs under a
    # mozilla.org subdomain
    'security.W005',
    'security.W009',  # we know the SECRET_KEY is strong
]


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
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'session_csrf.context_processor',
                'atmo.context_processors.settings',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        }
    },
]

# Django-CSP
CSP_DEFAULT_SRC = (
    "'self'",
)
CSP_FONT_SRC = (
    "'self'",
    "'unsafe-inline'",
    'http://*.mozilla.net',
    'https://*.mozilla.net',
    'http://*.mozilla.org',
    'https://*.mozilla.org',
)
CSP_IMG_SRC = (
    "'self'",
    "data:",
    'http://*.mozilla.net',
    'https://*.mozilla.net',
    'http://*.mozilla.org',
    'https://*.mozilla.org',
)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",
    'http://*.mozilla.org',
    'https://*.mozilla.org',
    'http://*.mozilla.net',
    'https://*.mozilla.net',
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    'http://*.mozilla.org',
    'https://*.mozilla.org',
    'http://*.mozilla.net',
    'https://*.mozilla.net',
)

# This is needed to get a CRSF token in /admin
ANON_ALWAYS = True
