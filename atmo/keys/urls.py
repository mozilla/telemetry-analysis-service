# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf.urls import url
from .import views


urlpatterns = [
    url(r'^new/', views.new_key, name='keys-new'),
    url(r'^(?P<id>\d+)/delete/$', views.delete_key, name='keys-delete'),
    url(r'^(?P<id>\d+)/raw/$', views.detail_key, {'raw': True}, name='keys-raw'),
    url(r'^(?P<id>\d+)/$', views.detail_key, name='keys-detail'),
    url(r'^$', views.list_keys, name='keys-list'),
]
