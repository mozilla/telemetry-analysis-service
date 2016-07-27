from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views import static

from . import views

urlpatterns = [
    url(r'^$', views.dashboard),
    url(r'^login/', views.login),
    url(r'^admin/', include(admin.site.urls)),

    url(r'clusters/', include('analysis_service.clusters.urls')),
    url(r'jobs/', include('analysis_service.jobs.urls')),
    url(r'workers/', include('analysis_service.workers.urls')),

    # contribute.json url
    url(r'^(?P<path>contribute\.json)$', static.serve, {'document_root': settings.ROOT}),

    url(r'', include('django_browserid.urls')),
]
