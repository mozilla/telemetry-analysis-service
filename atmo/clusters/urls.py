from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^new/$', views.new_cluster, name='clusters-new'),
    url(r'^edit/$', views.edit_cluster, name='clusters-edit'),
    url(r'^delete/$', views.delete_cluster, name='clusters-delete'),
    url(r'^(?P<id>[0-9]+)/$', views.detail_cluster, name='clusters-detail'),
]
