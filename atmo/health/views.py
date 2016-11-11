# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf import settings
from django.core.checks.registry import registry as checks_registry
from django.core.checks import messages as checks_messages
from django.http import Http404, HttpResponse, JsonResponse

from . import get_version


def version(request):
    version_json = get_version()
    if version_json is None:
        raise Http404
    return JsonResponse(version_json)


def lbheartbeat(request):
    return HttpResponse()


def heartbeat(request):
    all_checks = checks_registry.get_checks(include_deployment_checks=not settings.DEBUG)

    details = {}
    statuses = {}
    level = 0

    for check in all_checks:
        detail = heartbeat_check_detail(check)
        statuses[check.__name__] = detail['status']
        level = max(level, detail['level'])
        if detail['level'] > 0:
            details[check.__name__] = detail

    if level < checks_messages.WARNING:
        status_code = 200
    else:
        status_code = 500

    payload = {
        'status': heartbeat_level_to_text(level),
        'checks': statuses,
        'details': details,
    }
    return JsonResponse(payload, status=status_code)


def heartbeat_level_to_text(level):
    statuses = {
        0: 'ok',
        checks_messages.DEBUG: 'debug',
        checks_messages.INFO: 'info',
        checks_messages.WARNING: 'warning',
        checks_messages.ERROR: 'error',
        checks_messages.CRITICAL: 'critical',
    }
    return statuses.get(level, 'unknown')


def heartbeat_check_detail(check):
    errors = check(app_configs=None)
    errors = list(filter(lambda e: e.id not in settings.SILENCED_SYSTEM_CHECKS, errors))
    level = max([0] + [e.level for e in errors])

    return {
        'status': heartbeat_level_to_text(level),
        'level': level,
        'messages': {e.id: e.msg for e in errors},
    }
