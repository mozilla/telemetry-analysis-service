# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.apps import AppConfig
from django.conf import settings

import session_csrf


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

        # Under some circumstances (e.g. when calling collectstatic)
        # REDIS_URL is not available and we can skip the job schedule registration.
        if settings.REDIS_URL:
            # This module  contains references to some orm models, so it's
            # safer to import it here.
            from .jobs import register_job_schedule
            # Register rq scheduled jobs
            register_job_schedule()
