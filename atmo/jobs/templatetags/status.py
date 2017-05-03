# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import template
from django.template.defaultfilters import stringfilter

from atmo.clusters.models import Cluster


register = template.Library()


@register.filter
@stringfilter
def status_icon(status):
    if status in Cluster.ACTIVE_STATUS_LIST:
        return 'glyphicon-play'
    elif status in Cluster.TERMINATED_STATUS_LIST:
        return 'glyphicon-stop'
    elif status in Cluster.FAILED_STATUS_LIST:
        return 'glyphicon-exclamation-sign'


@register.filter
@stringfilter
def status_color(status):
    if status in Cluster.ACTIVE_STATUS_LIST:
        return 'status-running'
    elif status in Cluster.FAILED_STATUS_LIST:
        return 'status-errors'
