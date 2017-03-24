from django import template
from furl import furl


register = template.Library()


@register.simple_tag
def url_update(url, **kwargs):
    if kwargs:
        new_url = furl(url)
        new_url.args.update(kwargs)
        return new_url.url

    return url
