# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import logging

from django.apps import AppConfig
from django.utils.module_loading import import_string

import django_rq
import session_csrf
import redis

DEFAULT_JOB_TIMEOUT = 15

logger = logging.getLogger("django")


job_schedule = {
    'delete_clusters': {
        'cron_string': '* * * * *',
        'func': 'atmo.clusters.jobs.delete_clusters',
        'timeout': 15,
    },
    'send_expiration_mails': {
        'cron_string': '*/5 * * * *',
        'func': 'atmo.clusters.jobs.send_expiration_mails',
        'timeout': 60,
    },
    'update_clusters_info': {
        'cron_string': '* * * * *',
        'func': 'atmo.clusters.jobs.update_clusters_info',
        'timeout': 15,
    },
    'run_jobs': {
        'cron_string': '* * * * *',
        'func': 'atmo.jobs.jobs.run_jobs',
        'timeout': 45,
    },
    'clean_orphan_obj_perms': {
        'cron_string': '30 3 * * *',
        'func': 'guardian.utils.clean_orphan_obj_perms',
        'timeout': 60,
    }
}


def register_job_schedule():
    """
    Register the RQ job schedule, and cancel all the old ones
    """
    scheduler = django_rq.get_scheduler()
    for job_id, params in list(job_schedule.items()):
        scheduler.cron(
            params['cron_string'],
            id=job_id,
            func=import_string(params['func']),
            timeout=params.get('timeout', DEFAULT_JOB_TIMEOUT)
        )
    for job in scheduler.get_jobs():
        if job.id not in job_schedule:
            scheduler.cancel(job)


class AtmoAppConfig(AppConfig):
    name = 'atmo'

    def ready(self):
        # The app is now ready. Include any monkey patches here.

        # Monkey patch CSRF to switch to session based CSRF. Session
        # based CSRF will prevent attacks from apps under the same
        # domain. If you're planning to host your app under it's own
        # domain you can remove session_csrf and use Django's CSRF
        # library. See also
        # https://github.com/mozilla/sugardough/issues/38
        session_csrf.monkeypatch()

        # Register rq scheduled jobs, if Redis is available
        try:
            connection = django_rq.get_connection('default')
            connection.ping()
        except redis.ConnectionError:
            logger.warning('Could not connect to Redis, not reigstering RQ jobs')
        else:
            register_job_schedule()


class KeysAppConfig(AppConfig):
    name = 'atmo.keys'
    label = 'keys'
    verbose_name = 'Keys'
