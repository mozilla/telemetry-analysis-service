from urllib.parse import urljoin

from django import template
from django.conf import settings

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
