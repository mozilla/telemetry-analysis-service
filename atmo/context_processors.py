# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import os
from django.conf import settings as django_settings
from django.contrib import messages
from django.utils.safestring import mark_safe


def settings(request):
    """
    Adds static-related context variables to the context.
    """
    return {'settings': django_settings}


def version(request):
    """
    Adds static-related context variables to the context.
    """
    heroku_slug_commit = os.environ.get('HEROKU_SLUG_COMMIT', None)
    if django_settings.VERSION and 'commit' in django_settings.VERSION:
        commit = django_settings.VERSION['commit']
        return {
            'version': django_settings.VERSION.get('version', None),
            'long_sha1': commit,
            'short_sha1': commit[:7]
        }
    elif heroku_slug_commit:
        return {
            'long_sha1': heroku_slug_commit,
            'short_sha1': heroku_slug_commit[:7]
        }
    else:
        return {}


def alerts(request):
    """
    Here be dragons, for who are bold enough to break systems and lose data
    """
    host = request.get_host()
    warning = """
        <h4>Here be dragons!</h4>
        This service is currently under development and may not be stable."""
    if any(hint in host for hint in ['stag', 'localhost', 'dev']):
        messages.warning(request, mark_safe(warning))
    return {}
