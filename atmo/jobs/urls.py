from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^new/', views.new_spark_job, name='jobs-new'),
    url(r'^edit/', views.edit_spark_job, name='jobs-edit'),
    url(r'^delete/', views.delete_spark_job, name='jobs-delete'),
    url(r'^(?P<id>[0-9]+)/$', views.detail_spark_job, name='jobs-detail'),
]
