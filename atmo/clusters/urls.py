from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^new/$', views.new_cluster, name='clusters-new'),
    url(r'^(?P<id>\d+)/edit/$', views.edit_cluster, name='clusters-edit'),
    url(r'^(?P<id>\d+)/terminate/$', views.terminate_cluster, name='clusters-terminate'),
    url(r'^(?P<id>\d+)/$', views.detail_cluster, name='clusters-detail'),
]
