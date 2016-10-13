from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^new/', views.new_spark_job, name='jobs-new'),
    url(r'^(?P<id>\d+)/edit/', views.edit_spark_job, name='jobs-edit'),
    url(r'^(?P<id>\d+)/delete/', views.delete_spark_job, name='jobs-delete'),
    url(r'^(?P<id>\d+)/$', views.detail_spark_job, name='jobs-detail'),
]
