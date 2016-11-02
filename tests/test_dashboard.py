# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta
import pytest

from django.core.urlresolvers import reverse
from django.utils import timezone

from atmo.clusters.models import Cluster
from atmo.jobs.models import SparkJob


@pytest.fixture
def dashboard_spark_jobs(now, test_user):
    for x in range(10):
        SparkJob.objects.create(
            identifier='test-spark-job-%s' % x,
            notebook_s3_key=u's3://test/test-notebook-%s.ipynb' % x,
            result_visibility='private',
            size=5,
            interval_in_hours=24,
            job_timeout=12,
            start_date=now - timedelta(hours=2, minutes=x),
            last_run_date=now - timedelta(hours=1, minutes=x),
            created_by=test_user,
        )


def test_dashboard_jobs(client, test_user, dashboard_spark_jobs):
    dashboard_url = reverse('dashboard')

    response = client.get(dashboard_url, follow=True)
    assert 'spark_jobs' in response.context
    assert response.context['spark_jobs'].count() == 10


def make_cluster(mocker, **kwargs):
    mocker.patch(
        'atmo.provisioning.cluster_stop',
        return_value=None,
    )
    mocker.patch('atmo.provisioning.cluster_start', return_value=u'12345')
    mocker.patch(
        'atmo.provisioning.cluster_info',
        return_value={
            'start_time': timezone.now(),
            'state': Cluster.STATUS_BOOTSTRAPPING,
            'public_dns': 'master.public.dns.name',
        },
    )
    Cluster.objects.create(
        size=5,
        public_key='ssh-rsa AAAAB3', **kwargs
    )


@pytest.fixture
def dashboard_clusters(mocker, now, test_user):
    for x in range(5):
        make_cluster(
            mocker=mocker,
            identifier='test-cluster-%s' % x,
            jobflow_id=u'j-%s' % x,
            created_by=test_user,
            most_recent_status=Cluster.STATUS_WAITING,
        )

    for x in range(5):
        make_cluster(
            mocker=mocker,
            identifier='test-cluster-%s' % x,
            jobflow_id=u'j-%s' % x,
            created_by=test_user,
            most_recent_status=Cluster.STATUS_TERMINATED,
        )
    make_cluster(
        mocker=mocker,
        identifier='test-cluster-%s' % x,
        jobflow_id=u'j-%s' % x,
        created_by=test_user,
        most_recent_status=Cluster.STATUS_TERMINATED_WITH_ERRORS,
    )


def test_dashboard_active_clusters(client, mocker, test_user, dashboard_clusters):
    dashboard_url = reverse('dashboard')
    response = client.get(dashboard_url, follow=True)
    # even though we've created both active and inactive clusters,
    # we only have 5, the active ones
    assert response.context['clusters'].count() == 5
    for cluster in response.context['clusters']:
        assert cluster.is_active  # checks most_recent_status

    response2 = client.get(dashboard_url + '?clusters=active', follow=True)
    assert (set(response.context['clusters'].values_list('pk', flat=True)) ==
            set(response2.context['clusters'].values_list('pk', flat=True)))


def test_dashboard_all_clusters(client, mocker, test_user, dashboard_clusters):
    dashboard_url = reverse('dashboard')
    response = client.get(dashboard_url + '?clusters=all', follow=True)
    # since we've created both active, failed and terminated clusters
    assert response.context['clusters'].count() == 11


def test_dashboard_failed_clusters(client, mocker, test_user,
                                   dashboard_clusters):
    dashboard_url = reverse('dashboard')
    response = client.get(dashboard_url + '?clusters=failed', follow=True)
    assert response.context['clusters'].count() == 1
    assert response.context['clusters'][0].is_failed


def test_dashboard_terminated_clusters(client, mocker, test_user,
                                       dashboard_clusters):
    dashboard_url = reverse('dashboard')
    response = client.get(dashboard_url + '?clusters=terminated', follow=True)
    # since we have created only 5 terminated clusters
    assert response.context['clusters'].count() == 5
    for cluster in response.context['clusters']:
        assert cluster.is_terminated
