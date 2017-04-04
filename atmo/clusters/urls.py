# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^new/$', views.new_cluster, name='clusters-new'),
    url(r'^(?P<id>\d+)/extend/$', views.extend_cluster, name='clusters-extend'),
    url(r'^(?P<id>\d+)/terminate/$', views.terminate_cluster, name='clusters-terminate'),
    url(r'^(?P<id>\d+)/$', views.detail_cluster, name='clusters-detail'),
]
