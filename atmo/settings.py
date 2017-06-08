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
import logging
import os
import subprocess
from collections import OrderedDict
from datetime import timedelta

from celery.schedules import crontab
from configurations import Configuration, values
from django.contrib.messages import constants as messages
from django.core.urlresolvers import reverse_lazy
from dockerflow.version import get_version
from raven.transport.requests import RequestsHTTPTransport


class Celery:
    """
    The Celery specific Django settings.
    """
    #: The Celery broker transport options
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        # only send messages to actual virtual AMQP host instead of all
        'fanout_prefix': True,
        # have the workers only subscribe to worker related events (less network traffic)
        'fanout_patterns': True,
        # 8 days, since that's longer than our biggest interval to schedule a task (a week)
        # this is needed to be able to use ETAs and countdowns
        # http://docs.celeryproject.org/en/latest/getting-started/brokers/redis.html#id1
        'visibility_timeout': 8 * 24 * 60 * 60,
    }
    #: Use the django_celery_results database backend.
    CELERY_RESULT_BACKEND = 'django-db'
    #: Throw away task results after two weeks, for debugging purposes.
    CELERY_RESULT_EXPIRES = timedelta(days=14)
    #: Track if a task has been started, not only pending etc.
    CELERY_TASK_TRACK_STARTED = True
    #: Add a 5 minute soft timeout to all Celery tasks.
    CELERY_TASK_SOFT_TIME_LIMIT = 60 * 5
    #: And a 10 minute hard timeout.
    CELERY_TASK_TIME_LIMIT = CELERY_TASK_SOFT_TIME_LIMIT * 2
    #: Send SENT events as well to know when the task has left the scheduler.
    CELERY_TASK_SEND_SENT_EVENT = True
    #: Completely disable the rate limiting feature since it's costly
    CELERY_WORKER_DISABLE_RATE_LIMITS = True
    #: Stop hijacking the root logger so Sentry works.
    CELERY_WORKER_HIJACK_ROOT_LOGGER = False
    #: The scheduler to use for periodic and scheduled tasks.
    CELERY_BEAT_SCHEDULER = 'redbeat.RedBeatScheduler'
    #: Maximum time to sleep between re-checking the schedule
    CELERY_BEAT_MAX_LOOP_INTERVAL = 5  #: redbeat likes fast loops
    #: Unless refreshed the lock will expire after this time
    CELERY_REDBEAT_LOCK_TIMEOUT = CELERY_BEAT_MAX_LOOP_INTERVAL * 5
    #: The default/initial schedule to use.
    CELERY_BEAT_SCHEDULE = {
        'expire_jobs': {
            'schedule': crontab(minute='*'),
            'task': 'atmo.jobs.tasks.expire_jobs',
            'options': {
                'soft_time_limit': 15,
                'expires': 40,
            },
        },
        'deactivate_clusters': {
            'schedule': crontab(minute='*'),
            'task': 'atmo.clusters.tasks.deactivate_clusters',
            'options': {
                'soft_time_limit': 15,
                'expires': 40,
            },
        },
        'send_expiration_mails': {
            'schedule': crontab(minute='*/5'),  # every 5 minutes
            'task': 'atmo.clusters.tasks.send_expiration_mails',
            'options': {
                'expires': 4 * 60,
            },
        },
        'send_run_alert_mails': {
            'schedule': crontab(minute='*'),
            'task': 'atmo.jobs.tasks.send_run_alert_mails',
            'options': {
                'expires': 40,
            },
        },
        'update_clusters': {
            'schedule': crontab(minute='*/5'),  # update max_retries in task when changing!
            'task': 'atmo.clusters.tasks.update_clusters',
            'options': {
                'soft_time_limit': int(4.5 * 60),
                'expires': 3 * 60,
            },
        },
        'update_jobs_statuses': {
            'schedule': crontab(minute='*/15'),  # update max_retries in task when changing!
            'task': 'atmo.jobs.tasks.update_jobs_statuses',
            'options': {
                'soft_time_limit': int(14.5 * 60),
                'expires': 10 * 60,
            },
        },
        'clean_orphan_obj_perms': {
            'schedule': crontab(minute=30, hour=3),
            'task': 'atmo.tasks.cleanup_permissions',
        }
    }


class Constance:
    "Constance settings"
    CONSTANCE_BACKEND = 'constance.backends.redisd.RedisBackend'

    #: Using the django-redis connection function for the backend.
    CONSTANCE_REDIS_CONNECTION_CLASS = 'django_redis.get_redis_connection'

    #: Adds custom widget for announcements.
    CONSTANCE_ADDITIONAL_FIELDS = {
        'announcement_styles': ['django.forms.fields.ChoiceField', {
            'widget': 'django.forms.Select',
            'choices': (
                ('success', 'success (green)'),
                ('info', 'info (blue)'),
                ('warning', 'warning (yellow)'),
                ('danger', 'danger (red)'),
            )
        }],
        'announcement_title': ['django.forms.fields.CharField', {
            'widget': 'django.forms.TextInput',
        }],
    }

    #: The default config values.
    CONSTANCE_CONFIG = OrderedDict([
        ('ANNOUNCEMENT_ENABLED', (
            False,
            'Whether to show the announcement on every page.',
        )),
        ('ANNOUNCMENT_STYLE', (
            'info',
            'The style of the announcement.',
            'announcement_styles',
        )),
        ('ANNOUNCEMENT_TITLE', (
            'Announcement',
            'The announcement title.',
            'announcement_title',
        )),
        ('ANNOUNCEMENT_CONTENT_MARKDOWN', (
            False,
            'Whether the announcement content should be '
            'rendered as CommonMark (Markdown).',
        )),
        ('ANNOUNCEMENT_CONTENT', (
            '',
            'The announcement content.',
        )),
        ('AWS_USE_SPOT_INSTANCES', (
            True,
            'Whether to use spot instances on AWS',
        )),
        ('AWS_SPOT_BID_CORE', (
            0.84,
            'The spot instance bid price for the cluster workers',
        )),
        ('AWS_EFS_DNS', (
            'fs-616ca0c8.efs.us-west-2.amazonaws.com',  # the current dev instance of EFS
            'The DNS name of the EFS mount for EMR clusters'
        )),
    ])

    #: Some fieldsets for the config values.
    CONSTANCE_CONFIG_FIELDSETS = OrderedDict([
        ('Announcements', (
            'ANNOUNCEMENT_ENABLED',
            'ANNOUNCMENT_STYLE',
            'ANNOUNCEMENT_TITLE',
            'ANNOUNCEMENT_CONTENT',
            'ANNOUNCEMENT_CONTENT_MARKDOWN',
        )),
        ('AWS', (
            'AWS_USE_SPOT_INSTANCES',
            'AWS_SPOT_BID_CORE',
            'AWS_EFS_DNS',
        )),
    ])


class AWS:
    "AWS settings"

    #: The AWS config values.
    AWS_CONFIG = {
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
        ),
        'SPARK_INSTANCE_PROFILE': 'telemetry-spark-cloudformation-'
                                  'TelemetrySparkInstanceProfile-1SATUBVEXG7E3',
        'SPARK_EMR_BUCKET': 'telemetry-spark-emr-2',
        'INSTANCE_APP_TAG': 'telemetry-analysis-worker-instance',
        'EMAIL_SOURCE': 'telemetry-alerts@mozilla.com',
        'MAX_CLUSTER_SIZE': 30,
        'MAX_CLUSTER_LIFETIME': 24,

        # Tags for accounting purposes
        'ACCOUNTING_APP_TAG': 'telemetry-analysis',
        'ACCOUNTING_TYPE_TAG': 'worker',

        # Buckets for storing S3 data
        'CODE_BUCKET': 'telemetry-analysis-code-2',
        'PUBLIC_DATA_BUCKET': 'telemetry-public-analysis-2',
        'PRIVATE_DATA_BUCKET': 'telemetry-private-analysis-2',
        'LOG_BUCKET': 'telemetry-analysis-logs-2'
    }
    #: The URL of the S3 bucket with public job results.
    PUBLIC_DATA_URL = (
        'https://s3-%s.amazonaws.com/%s/' %
        (AWS_CONFIG['AWS_REGION'], AWS_CONFIG['PUBLIC_DATA_BUCKET'])
    )
    #: The URL to show public job results with.
    PUBLIC_NB_URL = (
        'https://nbviewer.jupyter.org/url/s3-%s.amazonaws.com/%s/' %
        (AWS_CONFIG['AWS_REGION'], AWS_CONFIG['PUBLIC_DATA_BUCKET'])
    )


class CSP:
    "CSP settings"
    CSP_DEFAULT_SRC = (
        "'self'",
    )
    CSP_FONT_SRC = (
        "'self'",
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
        'https://sentry.prod.mozaws.net',
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
    CSP_CONNECT_SRC = (
        "'self'",
        'https://sentry.prod.mozaws.net',
    )


class Core(AWS, Celery, Constance, CSP, Configuration):
    """Configuration that will never change per-environment."""

    #: The directory in which the settings file reside.
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    #: Build paths inside the project like this: os.path.join(BASE_DIR, ...)
    BASE_DIR = os.path.dirname(THIS_DIR)

    #: The current ATMO version.
    VERSION = get_version(BASE_DIR)

    #: Using the default first site found by django.contrib.sites
    SITE_ID = 1

    #: The installed apps.
    INSTALLED_APPS = [
        # Project specific apps
        'atmo.apps.AtmoAppConfig',
        'atmo.clusters',
        'atmo.jobs',
        'atmo.apps.KeysAppConfig',
        'atmo.users',

        # Third party apps
        'allauth',
        'allauth.account',
        'allauth.socialaccount',
        'guardian',
        'constance',
        'constance.backends.database',
        'dockerflow.django',
        'django_celery_monitor',
        'django_celery_results',
        'flat_responsive',

        # Django apps
        'django.contrib.sites',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
    ]

    MIDDLEWARE = (
        'django.middleware.security.SecurityMiddleware',
        'dockerflow.django.middleware.DockerflowMiddleware',
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

    DEFAULT_FROM_EMAIL = 'telemetry-alerts@mozilla.com'

    # The email backend.
    EMAIL_BACKEND = 'django_amazon_ses.backends.boto.EmailBackend'

    EMAIL_SUBJECT_PREFIX = '[Telemetry Analysis Service] '

    @property
    def DJANGO_AMAZON_SES_REGION(self):
        return self.AWS_CONFIG['AWS_REGION']

    #: Adds the django-allauth authentication backend.
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
    ACCOUNT_EMAIL_SUBJECT_PREFIX = EMAIL_SUBJECT_PREFIX
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

    MESSAGE_TAGS = {
        messages.ERROR: 'danger'
    }

    # Raise PermissionDenied in get_40x_or_None which is used
    # by permission_required decorator
    GUARDIAN_RAISE_403 = True

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
        'bootstrap-datetime-picker': [
            'css/*.css',
            'js/*.js',
        ],
        'clipboard': ['dist/clipboard.min.js'],
        'jquery': ['dist/*.js'],
        'marked': ['marked.min.js'],
        'moment': ['min/moment.min.js'],
        'notebookjs': ['notebook.min.js'],
        'parsleyjs': ['dist/parsley.min.js'],
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
                    'constance.context_processors.config',
                ],
                'loaders': [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ],
                'libraries': {
                    'atmo': 'atmo.templatetags',
                },
            }
        },
    ]


class Base(Core):
    """Configuration that may change per-environment, some with defaults."""

    SECRET_KEY = values.SecretValue()

    DEBUG = values.BooleanValue(default=False)

    ALLOWED_HOSTS = values.ListValue([])

    #: The URL under which this instance is running
    SITE_URL = values.URLValue('http://localhost:8000')

    # Database
    # https://docs.djangoproject.com/en/1.9/ref/settings/#databases
    DATABASES = values.DatabaseURLValue('postgres://postgres@db/postgres')

    REDIS_URL_DEFAULT = 'redis://redis:6379/1'
    CACHES = values.CacheURLValue(
        REDIS_URL_DEFAULT,
        environ_prefix=None,
        environ_name='REDIS_URL',
    )
    # Use redis as the Celery broker.
    CELERY_BROKER_URL = os.environ.get('REDIS_URL', REDIS_URL_DEFAULT)

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
                'django.server': {
                    '()': 'django.utils.log.ServerFormatter',
                    'format': '[%(server_time)s] %(message)s',
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
                'django.server': {
                    'level': 'INFO',
                    'class': 'logging.StreamHandler',
                    'formatter': 'django.server',
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
                'django.server': {
                    'handlers': ['django.server'],
                    'level': 'INFO',
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
                'celery.task': {
                    'level': 'DEBUG',
                    'handlers': ['console'],
                    'propagate': False,
                },
                'redbeat.schedulers': {
                    'level': 'DEBUG',
                    'handlers': ['console'],
                    'propagate': False,
                },
                'request.summary': {
                    'level': 'DEBUG',
                    'handlers': ['console'],
                    'propagate': False,
                },
            },
        }


class Dev(Base):
    "Configuration to be used during development and base class for testing"

    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

    @classmethod
    def post_setup(cls):
        super().post_setup()
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

    @property
    def VERSION(self):
        output = subprocess.check_output(['git', 'describe', '--tags', '--abbrev=0'])
        if output:
            return {'version': output.decode().strip()}
        else:
            return {}


class Test(Dev):
    "Configuration to be used during testing"
    DEBUG = False

    SECRET_KEY = values.Value('not-so-secret-after-all')

    PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.MD5PasswordHasher',
    )

    MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'


class Stage(Base):
    "Configuration to be used in stage environment"

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
        # require encrypted connections to Postgres
        DATABASES = super().DATABASES.value.copy()
        DATABASES['default'].setdefault('OPTIONS', {})['sslmode'] = 'require'
        return DATABASES

    # Sentry setup
    SENTRY_DSN = values.Value(environ_prefix=None)
    SENTRY_PUBLIC_DSN = values.Value(environ_prefix=None)
    SENTRY_CELERY_LOGLEVEL = logging.INFO

    MIDDLEWARE = (
        'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
    ) + Base.MIDDLEWARE

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
                ''
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
    "Configuration to be used in prod environment"

    @property
    def CONSTANCE_CONFIG(self):
        config = super().CONSTANCE_CONFIG.copy()
        override = {
            'AWS_EFS_DNS': (
                'fs-d0c30f79.efs.us-west-2.amazonaws.com',  # the current prod instance of EFS
                'The DNS name of the EFS mount for EMR clusters'
            )
        }
        config.update(override)
        return config


class Heroku(Prod):
    "Configuration to be used in prod environment"
    STATIC_ROOT = os.path.join(Prod.BASE_DIR, 'staticfiles')
    NPM_ROOT_PATH = Prod.BASE_DIR


class Build(Prod):
    "Configuration to be used in build (!) environment"
    SECRET_KEY = values.Value('not-so-secret-after-all')


class Docs(Test):
    "Configuration to be used in the documentation environment"
    DOTENV = None
