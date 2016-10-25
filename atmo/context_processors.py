# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import atmo
from django.conf import settings as django_settings


def settings(request):
    """
    Adds static-related context variables to the context.
    """
    return {'settings': django_settings}


def revision(request):
    """
    Adds static-related context variables to the context.
    """
    revision = atmo.get_revision()
    if revision:
        return {
            'long_sha1': revision,
            'short_sha1': revision[:7]
        }
    return {}
