# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from urllib.parse import urljoin

from django import template
from django.conf import settings

import commonmark
from furl import furl


register = template.Library()


@register.simple_tag
def url_update(url, **kwargs):
    """
    A Django template tag to update the query parameters for the given URL.
    """
    if kwargs:
        new_url = furl(url)
        new_url.args.update(kwargs)
        return new_url.url

    return url


@register.filter
def full_url(url):
    """
    A Django template filter to prepend the given URL path with the full
    site URL.
    """
    return urljoin(settings.SITE_URL, url)


@register.filter
def markdown(content):
    """
    A Django template filter to render the given content as Markdown.
    """
    return commonmark.commonmark(content)
