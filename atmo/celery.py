import functools
import os
import random
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atmo.settings')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Dev')

import configurations  # noqa
configurations.setup()


class ExpoBackoffFullJitter:
    """
    Implement fully jittered exponential retries.

    See for more infos:

    - https://www.awsarchitectureblog.com/2015/03/backoff.html
    - https://github.com/awslabs/aws-arch-backoff-simulator

    Copyright 2015 Amazon

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
    """
    def __init__(self, base, cap):
        self.base = base
        self.cap = cap

    def expo(self, n):
        return min(self.cap, pow(2, n) * self.base)

    def backoff(self, n):
        v = self.expo(n)
        return random.uniform(0, v)


class AtmoCelery(Celery):
    """
    A custom Celery class to implement exponential backoff retries.
    """
    def autoretry_task(self, autoretry_on=None, *args, **opts):
        if autoretry_on is None:
            autoretry_on = Exception
        super_task = super().task

        def decorator(func):
            bind_passed = 'bind' in opts
            opts['bind'] = True

            @super_task(*args, **opts)
            @functools.wraps(func)
            def wrapper(task, *fargs, **fkwargs):
                try:
                    if bind_passed:
                        return func(task, *fargs, **fkwargs)
                    else:
                        return func(*fargs, **fkwargs)
                except autoretry_on as exc:
                    backoff = ExpoBackoffFullJitter(base=1, cap=60 * 60)
                    countdown = backoff.backoff(task.request.retries)
                    task.retry(
                        exc=exc,
                        args=fargs,
                        kwargs=fkwargs,
                        countdown=countdown,
                    )
            return wrapper
        return decorator


celery = AtmoCelery('atmo')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
celery.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django celery configs.
celery.autodiscover_tasks()
