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


class WhatsNew:

    def __init__(self):
        self.path = os.path.join(settings.BASE_DIR, 'WHATSNEW.md')
        self.parser = CommonMark.Parser()
        self.renderer = CommonMark.HtmlRenderer()
        self.cookie_name = 'whatsnew_current'

    @cached_property
    def ast(self):
        with open(self.path, 'r') as whatsnew_file:
            content = whatsnew_file.read()
            return self.parser.parse(content)

    @cached_property
    def latest(self):
        version = self.ast.first_child.literal
        if not version:
            version = self.ast.first_child.first_child.literal
            if not version:
                version = '0.0'
        return version

    def render(self):
        return self.renderer.render(self.ast)

    def update(self, request, response):
        if not self.uptodate(request):
            response.set_cookie(self.cookie_name, self.latest)

    def current(self, request):
        return request.COOKIES.get(self.cookie_name) or ''

    def uptodate(self, request):
        return parse_version(self.latest) <= parse_version(self.current(request))


def list_whatsnew(request):
    whatsnew = WhatsNew()

    if request.is_ajax():
        response = HttpResponse(whatsnew.render())
    else:
        context = {'whatsnew': whatsnew}
        response = render(request, 'atmo/whatsnew/list.html', context)

    whatsnew.update(request, response)
    return response


def check_whatsnew(request):
    whatsnew = WhatsNew()
    if whatsnew.uptodate(request):
        return HttpResponse('ok')
    else:
        return HttpResponse('meh')
