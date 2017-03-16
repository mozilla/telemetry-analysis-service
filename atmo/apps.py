# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import logging

import session_csrf
from django.apps import AppConfig

DEFAULT_JOB_TIMEOUT = 15

logger = logging.getLogger("django")


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


class KeysAppConfig(AppConfig):
    name = 'atmo.keys'
    label = 'keys'
    verbose_name = 'Keys'
