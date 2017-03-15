# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^new/', views.new_spark_job, name='jobs-new'),
    url(r'^identifier-available/', views.check_identifier_available,
        name='jobs-identifier-available'),
    url(r'^(?P<id>\d+)/delete/', views.delete_spark_job, name='jobs-delete'),
    url(r'^(?P<id>\d+)/download/', views.download_spark_job, name='jobs-download'),
    url(r'^(?P<id>\d+)/edit/', views.edit_spark_job, name='jobs-edit'),
    url(r'^(?P<id>\d+)/$', views.detail_spark_job, name='jobs-detail'),
]
