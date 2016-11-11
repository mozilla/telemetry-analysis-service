# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.core.checks import Info, Warning, Error, register as register_check
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError


from django_redis import get_redis_connection
import redis


INFO_CANT_CHECK_MIGRATIONS = 'atmo.health.I001'
WARNING_UNAPPLIED_MIGRATION = 'atmo.health.W001'
ERROR_CANNOT_CONNECT_DATABASE = 'atmo.health.E001'
ERROR_UNUSABLE_DATABASE = 'atmo.health.E002'
ERROR_MISCONFIGURED_DATABASE = 'atmo.health.E003'
ERROR_CANNOT_CONNECT_REDIS = 'atmo.health.E004'
ERROR_MISSING_REDIS_CLIENT = 'atmo.health.E005'
ERROR_MISCONFIGURED_REDIS = 'atmo.health.E006'
ERROR_REDIS_PING_FAILED = 'atmo.health.E007'


def database_connected(app_configs, **kwargs):
    errors = []

    try:
        connection.ensure_connection()
    except OperationalError as e:
        msg = 'Could not connect to database: {!s}'.format(e)
        errors.append(Error(msg, id=ERROR_CANNOT_CONNECT_DATABASE))
    except ImproperlyConfigured as e:
        msg = 'Datbase misconfigured: "{!s}"'.format(e)
        errors.append(Error(msg, id=ERROR_MISCONFIGURED_DATABASE))
    else:
        if not connection.is_usable():
            errors.append(Error('Database connection is not usable', id=ERROR_UNUSABLE_DATABASE))

    return errors


def migrations_applied(app_configs, **kwargs):
    from django.db.migrations.loader import MigrationLoader
    errors = []

    # Load migrations from disk/DB
    try:
        loader = MigrationLoader(connection, ignore_no_migrations=True)
    except (ImproperlyConfigured, ProgrammingError, OperationalError):
        msg = "Can't connect to database to check migrations"
        return [Info(msg, id=INFO_CANT_CHECK_MIGRATIONS)]
    graph = loader.graph

    if app_configs:
        app_labels = [app.label for app in app_configs]
    else:
        app_labels = loader.migrated_apps

    for node, migration in graph.nodes.items():
        if migration.app_label not in app_labels:
            continue
        if node not in loader.applied_migrations:
            msg = 'Unapplied migration {}'.format(migration)
            # NB: This *must* be a Warning, not an Error, because Errors
            # prevent migrations from being run.
            errors.append(Warning(msg, id=WARNING_UNAPPLIED_MIGRATION))

    return errors


def redis_connected(app_configs, **kwargs):
    errors = []

    try:
        connection = get_redis_connection('default')
    except redis.ConnectionError as e:
        msg = 'Could not connect to redis: {!s}'.format(e)
        errors.append(Error(msg, id=ERROR_CANNOT_CONNECT_REDIS))
    except NotImplementedError as e:
        msg = 'Redis client not available: {!s}'.format(e)
        errors.append(Error(msg, id=ERROR_MISSING_REDIS_CLIENT))
    except ImproperlyConfigured as e:
        msg = 'Redis misconfigured: "{!s}"'.format(e)
        errors.append(Error(msg, id=ERROR_MISCONFIGURED_REDIS))
    else:
        result = connection.ping()
        if not result:
            msg = 'Redis ping failed'
            errors.append(Error(msg, id=ERROR_REDIS_PING_FAILED))
    return errors


def register():
    register_check(database_connected)
    register_check(migrations_applied)
    register_check(redis_connected)
