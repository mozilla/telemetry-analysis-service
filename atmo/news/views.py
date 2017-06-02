# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import os

import CommonMark
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.functional import cached_property
from pkg_resources import parse_version


class News:
    """
    Encapsulate the rendering of the news document ``NEWS.md``.
    """
    def __init__(self):
        self.path = os.path.join(settings.BASE_DIR, 'NEWS.md')
        self.parser = CommonMark.Parser()
        self.renderer = CommonMark.HtmlRenderer()
        self.cookie_name = 'news_current'

    @cached_property
    def ast(self):
        """
        Return (and cache for repeated querying) the Markdown AST
        of the ``NEWS.md`` file.
        """
        with open(self.path, 'r') as news_file:
            content = news_file.read()
            return self.parser.parse(content)

    @cached_property
    def latest(self):
        """
        Return the latest version found in the ``NEWS.md`` file.
        """
        version = self.ast.first_child.literal
        if not version:
            version = self.ast.first_child.first_child.literal
            if not version:
                version = '0.0'
        return version

    def render(self):
        "Render the ``NEWS.md`` file as a HTML."
        return self.renderer.render(self.ast)

    def update(self, request, response):
        "Set the cookie for the given request with the latest seen version."
        if not self.uptodate(request):
            response.set_cookie(self.cookie_name, self.latest)

    def current(self, request):
        "Return the latest seen version or nothing."
        return request.COOKIES.get(self.cookie_name) or ''

    def uptodate(self, request):
        "Return whether the current is newer than the last seen version."
        return parse_version(self.latest) <= parse_version(self.current(request))


def list_news(request):
    """
    View to list all news and optionally render only part of the
    template for AJAX requests.
    """
    news = News()

    if request.is_ajax():
        response = HttpResponse(news.render())
    else:
        context = {'news': news}
        response = render(request, 'atmo/news/list.html', context)

    news.update(request, response)
    return response


def check_news(request):
    """
    View to check if the current user has seen the latest "News" section
    and return either `'ok'` or `'meh'` as a string.
    """
    news = News()
    if news.uptodate(request):
        return HttpResponse('ok')
    else:
        return HttpResponse('meh')
