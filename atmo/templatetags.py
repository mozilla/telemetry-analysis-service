# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from urllib.parse import urljoin

from django import template
from django.conf import settings

import CommonMark
from furl import furl


register = template.Library()


@register.simple_tag
def url_update(url, **kwargs):
    if kwargs:
        new_url = furl(url)
        new_url.args.update(kwargs)
        return new_url.url

    return url


@register.filter
def full_url(url):
    return urljoin(settings.SITE_URL, url)


@register.filter
def markdown(content):
    return CommonMark.commonmark(content)
