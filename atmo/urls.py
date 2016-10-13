# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views import static

from . import views

urlpatterns = [
    url(r'^$', views.dashboard, name='dashboard'),
    url(r'^admin/rq/', include('django_rq.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url(r'clusters/', include('atmo.clusters.urls')),
    url(r'jobs/', include('atmo.jobs.urls')),

    # contribute.json url
    url(r'^(?P<path>contribute\.json)$', static.serve, {'document_root': settings.BASE_DIR}),
    url(r'^(?P<path>revision\.txt)$', static.serve, {'document_root': settings.BASE_DIR}),

    url(r'^accounts/', include('allauth.urls')),
]
