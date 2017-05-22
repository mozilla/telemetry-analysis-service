# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import os
from celery import Celery
from celery.five import string_t
from celery.utils.time import maybe_iso8601


# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atmo.settings')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Dev')

import configurations  # noqa
configurations.setup()


class AtmoCelery(Celery):
    """
    A custom Celery class to implement exponential backoff retries.
    """
    def send_task(self, *args, **kwargs):
        # HACK: This needs to be removed once Celery > 4.0.2 is out:
        # see https://github.com/celery/celery/issues/3734
        # and https://github.com/celery/celery/pull/3790
        expires = kwargs.get('expires')
        if isinstance(expires, string_t):
            kwargs['expires'] = maybe_iso8601(expires)
        return super().send_task(*args, **kwargs)


celery = AtmoCelery('atmo')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
celery.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django celery configs.
celery.autodiscover_tasks()
