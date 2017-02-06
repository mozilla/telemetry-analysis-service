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

from configurations import Configuration, values
from django.contrib.messages import constants as messages
from django.core.urlresolvers import reverse_lazy
from raven.transport.requests import RequestsHTTPTransport
from dockerflow.version import get_version


class Constance(object):
    "Constance settings"
    CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

    CONSTANCE_CONFIG = {
        'AWS_USE_SPOT_INSTANCES': (
            True,
            'Whether to use spot instances on AWS',
        ),
        'AWS_SPOT_BID_CORE': (
            0.84,
            'The spot instance bid price for the cluster workers',
        ),
    }

    CONSTANCE_DATABASE_PREFIX = 'atmo:'

    CONSTANCE_DATABASE_CACHE_BACKEND = 'default'


class AWS(object):
    "AWS configuration"

    AWS_CONFIG = {
        # AWS EC2 configuration
        'AWS_REGION': 'us-west-2',
        'EC2_KEY_NAME': '20161025-dataops-dev',

        # EMR configuration
        # Master and slave instance types should be the same as the telemetry
        # setup bootstrap action depends on it to autotune the cluster.
        'MASTER_INSTANCE_TYPE': 'c3.4xlarge',
        'WORKER_INSTANCE_TYPE': 'c3.4xlarge',
        # available EMR releases, to be used as choices for Spark jobs and clusters
        # forms. Please keep the latest (newest) as the first item
        'EMR_RELEASES': (
            '5.2.1',
            '5.0.0',
            '4.5.0',
        ),
        'SPARK_INSTANCE_PROFILE': 'telemetry-spark-cloudformation-'
                                  'TelemetrySparkInstanceProfile-1SATUBVEXG7E3',
        'SPARK_EMR_BUCKET': 'telemetry-spark-emr-2',
        'INSTANCE_APP_TAG': 'telemetry-analysis-worker-instance',
        'EMAIL_SOURCE': 'telemetry-alerts@mozilla.com',
        'MAX_CLUSTER_SIZE': 30,

        # Tags for accounting purposes
        'ACCOUNTING_APP_TAG': 'telemetry-analysis',
        'ACCOUNTING_TYPE_TAG': 'worker',

        # Buckets for storing S3 data
        'CODE_BUCKET': 'telemetry-analysis-code-2',
        'PUBLIC_DATA_BUCKET': 'telemetry-public-analysis-2',
        'PRIVATE_DATA_BUCKET': 'telemetry-private-analysis-2',
        'LOG_BUCKET':          'telemetry-analysis-logs-2'
    }
    PUBLIC_DATA_URL = 'https://s3-{}.amazonaws.com/{}/'.format(AWS_CONFIG['AWS_REGION'],
                                                               AWS_CONFIG['PUBLIC_DATA_BUCKET'])
    PUBLIC_NB_URL = 'https://nbviewer.jupyter.org/url/s3-{}.amazonaws.com/{}/'.format(
        AWS_CONFIG['AWS_REGION'],
        AWS_CONFIG['PUBLIC_DATA_BUCKET'])


class CSP(object):
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
        'http://*.mozilla.org',
        'https://*.mozilla.org',
        'http://*.mozilla.net',
        'https://*.mozilla.net',
        'https://cdn.ravenjs.com',
    )
    CSP_STYLE_SRC = (
        "'self'",
        "'unsafe-inline'",
        'http://*.mozilla.org',
        'https://*.mozilla.org',
        'http://*.mozilla.net',
        'https://*.mozilla.net',
    )


class Core(Constance, CSP, AWS, Configuration):
    """Settings that will never change per-environment."""

    # Build paths inside the project like this: os.path.join(BASE_DIR, ...)
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(THIS_DIR)

    VERSION = get_version(BASE_DIR)

    # Using the default first site found by django.contrib.sites
    SITE_ID = 1

    INSTALLED_APPS = [
        # Project specific apps
        'atmo.apps.AtmoAppConfig',
        'atmo.clusters',
        'atmo.jobs',
        'atmo.apps.KeysAppConfig',
        'atmo.users',

        # Third party apps
        'django_rq',
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        'guardian',
        'constance',
        'constance.backends.database',
        'dockerflow.django',

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
        'dockerflow.django.middleware.DockerflowMiddleware',
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

    RQ_SHOW_ADMIN_LINK = True

    # Add the django-allauth authentication backend.
    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
        'allauth.account.auth_backends.AuthenticationBackend',
        'guardian.backends.ObjectPermissionBackend',
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
    ACCOUNT_USER_DISPLAY = 'atmo.users.utils.email_user_display'

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

    MESSAGE_TAGS = {
        messages.ERROR: 'danger'
    }

    # render the 403.html file
    GUARDIAN_RENDER_403 = True

    # Internationalization
    # https://docs.djangoproject.com/en/1.9/topics/i18n/
    LANGUAGE_CODE = 'en-us'
    TIME_ZONE = 'UTC'
    USE_I18N = False
    USE_L10N = False
    USE_TZ = True
    DATETIME_FORMAT = 'Y-m-d H:i'  # simplified ISO format since we assume UTC

    STATIC_ROOT = values.Value(default='/opt/static/')
    STATIC_URL = '/static/'
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    STATICFILES_FINDERS = [
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        'npm.finders.NpmFinder',
    ]

    NPM_ROOT_PATH = values.Value(default='/opt/npm/')
    NPM_STATIC_FILES_PREFIX = 'npm'
    NPM_FILE_PATTERNS = {
        'ansi_up': ['ansi_up.js'],
        'bootstrap': [
            'dist/fonts/*',
            'dist/css/*',
            'dist/js/bootstrap*.js',
        ],
        'bootstrap-confirmation2': ['bootstrap-confirmation.min.js'],
        'eonasdan-bootstrap-datetimepicker': [
            'build/css/bootstrap-datetimepicker.min.css',
            'build/js/*.js',
        ],
        'jquery': ['dist/*.js'],
        'marked': ['marked.min.js'],
        'moment': ['min/moment.min.js'],
        'notebookjs': ['notebook.min.js'],
        'prismjs': [
            'prism.js',
            'components/*.js',
            'plugins/autoloader/*.js',
            'themes/prism.css',
        ],
        'raven-js': [
            'dist/raven.*',
        ]
    }

    # the directory to have Whitenoise serve automatically on the root of the URL
    WHITENOISE_ROOT = os.path.join(THIS_DIR, 'static', 'public')

    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'

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
                    'atmo.context_processors.version',
                    'atmo.context_processors.alerts',
                ],
                'loaders': [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ],
            }
        },
    ]


class Base(Core):
    """Settings that may change per-environment, some with defaults."""

    SECRET_KEY = values.SecretValue()

    DEBUG = values.BooleanValue(default=False)

    ALLOWED_HOSTS = values.ListValue([])

    # The URL under which this instance is running
    SITE_URL = values.URLValue('http://localhost:8000')

    # Database
    # https://docs.djangoproject.com/en/1.9/ref/settings/#databases
    DATABASES = values.DatabaseURLValue('postgres://postgres@db/postgres')

    RQ_QUEUES = {
        'default': {
            'USE_REDIS_CACHE': 'default',
        }
    }

    CACHES = values.CacheURLValue(
        'redis://redis:6379/0',
        environ_prefix=None,
        environ_name='REDIS_URL',
    )

    LOGGING_USE_JSON = values.BooleanValue(False)

    def LOGGING(self):
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'json': {
                    '()': 'dockerflow.logging.JsonLogFormatter',
                    'logger_name': 'atmo',
                },
                'verbose': {
                    'format': '%(levelname)s %(asctime)s %(name)s %(message)s',
                },
            },
            'handlers': {
                'console': {
                    'level': 'DEBUG',
                    'class': 'logging.StreamHandler',
                    'formatter': 'json' if self.LOGGING_USE_JSON else 'verbose',
                },
                'sentry': {
                    'level': 'ERROR',
                    'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
                },
            },
            'loggers': {
                'root': {
                    'level': 'INFO',
                    'handlers': ['sentry', 'console'],
                },
                'django.db.backends': {
                    'level': 'ERROR',
                    'handlers': ['console'],
                    'propagate': False,
                },
                'raven': {
                    'level': 'DEBUG',
                    'handlers': ['console'],
                    'propagate': False,
                },
                'sentry.errors': {
                    'level': 'DEBUG',
                    'handlers': ['console'],
                    'propagate': False,
                },
                'atmo': {
                    'level': 'DEBUG',
                    'handlers': ['console'],
                    'propagate': False,
                },
                'rq': {
                    'handlers': ['console', 'sentry'],
                    'level': 'INFO',
                    'propagate': False,
                },
                'request.summary': {
                    'handlers': ['console'],
                    'level': 'DEBUG',
                    'propagate': False,
                },
            },
        }


class Dev(Base):
    """Configuration to be used during development and base class for testing"""

    @classmethod
    def post_setup(cls):
        super(Dev, cls).post_setup()
        # in case we don't find these AWS config variables in the environment
        # we load them from the .env file
        for param in ('ACCESS_KEY_ID', 'SECRET_ACCESS_KEY', 'DEFAULT_REGION'):
            if param not in os.environ:
                os.environ[param] = values.Value(
                    default='',
                    environ_name=param,
                    environ_prefix='AWS',
                )

    DOTENV = os.path.join(Core.BASE_DIR, '.env')


class Test(Dev):
    """Configuration to be used during testing"""
    CONSTANCE_BACKEND = 'constance.backends.redisd.RedisBackend'

    CONSTANCE_REDIS_CONNECTION = Dev.CACHES

    CONSTANCE_REDIS_CONNECTION_CLASS = 'django_redis.get_redis_connection'

    DEBUG = False

    SECRET_KEY = values.Value('not-so-secret-after-all')

    PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )

    MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'


class Stage(Base):
    """Configuration to be used in stage environment"""

    LOGGING_USE_JSON = True

    ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = int(timedelta(days=365).total_seconds())
    # Mark session and CSRF cookies as being HTTPS-only.
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    # This is needed to get a CRSF token in /admin
    ANON_ALWAYS = True

    @property
    def DATABASES(self):
        "require encrypted connections to Postgres"
        DATABASES = super(Stage, self).DATABASES.value.copy()
        DATABASES['default'].setdefault('OPTIONS', {})['sslmode'] = 'require'
        return DATABASES

    # Sentry setup
    SENTRY_DSN = values.Value(environ_prefix=None)
    SENTRY_PUBLIC_DSN = values.Value(environ_prefix=None)

    MIDDLEWARE_CLASSES = (
        'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
    ) + Base.MIDDLEWARE_CLASSES

    INSTALLED_APPS = Base.INSTALLED_APPS + [
        'raven.contrib.django.raven_compat',
    ]

    @property
    def RAVEN_CONFIG(self):
        config = {
            'dsn': self.SENTRY_DSN,
            'transport': RequestsHTTPTransport,
        }
        if self.VERSION:
            config['release'] = (
                self.VERSION.get('version') or
                self.VERSION.get('commit') or
                '',
            )
        return config

    # Report CSP reports to this URL that is only available in stage and prod
    CSP_REPORT_URI = '/__cspreport__'

    DOCKERFLOW_CHECKS = [
        'dockerflow.django.checks.check_database_connected',
        'dockerflow.django.checks.check_migrations_applied',
        'dockerflow.django.checks.check_redis_connected',
    ]


class Prod(Stage):
    """Configuration to be used in prod environment"""


class Heroku(Prod):
    """Configuration to be used in prod environment"""
    STATIC_ROOT = os.path.join(Prod.BASE_DIR, 'staticfiles')
    NPM_ROOT_PATH = Prod.BASE_DIR


class Build(Prod):
    """Configuration to be used in build (!) environment"""
    SECRET_KEY = values.Value('not-so-secret-after-all')
