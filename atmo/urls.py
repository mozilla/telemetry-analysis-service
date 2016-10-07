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
    url(r'workers/', include('atmo.workers.urls')),

    # contribute.json url
    url(r'^(?P<path>contribute\.json)$', static.serve, {'document_root': settings.BASE_DIR}),
    url(r'^(?P<path>revision\.txt)$', static.serve, {'document_root': settings.BASE_DIR}),

    url(r'^accounts/', include('allauth.urls')),
]
