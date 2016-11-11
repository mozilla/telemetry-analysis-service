# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views import generic, static

from . import views

handler500 = 'atmo.views.server_error'


urlpatterns = [
    url(r'^$', views.dashboard, name='dashboard'),
    url(r'^', include('atmo.health.urls')),
    url(r'^admin/rq/', include('django_rq.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url(r'clusters/', include('atmo.clusters.urls')),
    url(r'jobs/', include('atmo.jobs.urls')),

    # contribute.json url
    url(r'^(?P<path>contribute\.json)$', static.serve, {'document_root': settings.BASE_DIR}),
    url(r'^404/$', generic.TemplateView.as_view(template_name='404.html')),
    url(r'^500/$', generic.TemplateView.as_view(template_name='500.html')),

    url(r'^accounts/', include('allauth.urls')),
]
