# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

import pytest
from django.core.urlresolvers import reverse
from django.utils import timezone

from atmo.clusters.models import Cluster
from atmo.jobs.models import SparkJob
from atmo.views import server_error


@pytest.fixture
def dashboard_spark_jobs(now, test_user):
    for x in range(10):
        identifier = 'test-spark-job-%s' % x
        job = SparkJob.objects.create(
            identifier=identifier,
            notebook_s3_key='jobs/%s/test-notebook-%s.ipynb' % (identifier, x),
            result_visibility='private',
            size=5,
            interval_in_hours=24,
            job_timeout=12,
            start_date=now - timedelta(hours=2, minutes=x),
            created_by=test_user,
        )
        job.runs.create(
            scheduled_date=now - timedelta(hours=1, minutes=x),
        )


def test_dashboard_jobs(client, test_user, dashboard_spark_jobs):
    dashboard_url = reverse('dashboard')

    response = client.get(dashboard_url, follow=True)
    assert 'spark_jobs' in response.context
    assert response.context['spark_jobs'].count() == 10


def make_cluster(mocker, **kwargs):
    mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.stop',
        return_value=None,
    )
    mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.start',
        return_value='12345',
    )
    mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.info',
        return_value={
            'start_time': timezone.now(),
            'state': Cluster.STATUS_BOOTSTRAPPING,
            'state_change_reason': None,
            'public_dns': 'master.public.dns.name',
        },
    )
    Cluster.objects.create(
        size=5,
        **kwargs
    )


@pytest.fixture
def dashboard_clusters(mocker, now, test_user, ssh_key):
    for x in range(5):
        make_cluster(
            mocker=mocker,
            identifier='test-cluster-%s' % x,
            jobflow_id='j-%s' % x,
            created_by=test_user,
            most_recent_status=Cluster.STATUS_WAITING,
            ssh_key=ssh_key,
        )

    for x in range(5):
        make_cluster(
            mocker=mocker,
            identifier='test-cluster-%s' % x,
            jobflow_id='j-%s' % x,
            created_by=test_user,
            most_recent_status=Cluster.STATUS_TERMINATED,
            ssh_key=ssh_key,
        )
    make_cluster(
        mocker=mocker,
        identifier='test-cluster-%s' % x,
        jobflow_id='j-%s' % x,
        created_by=test_user,
        most_recent_status=Cluster.STATUS_TERMINATED_WITH_ERRORS,
        ssh_key=ssh_key,
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
    response3 = client.get(dashboard_url + '?clusters=foobar', follow=True)

    pks = set(response.context['clusters'].values_list('pk', flat=True))
    pks2 = set(response2.context['clusters'].values_list('pk', flat=True))
    pks3 = set(response3.context['clusters'].values_list('pk', flat=True))

    assert pks == pks2 == pks3


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


def test_server_error(rf):
    request = rf.get('/')
    response = server_error(request)
    assert response.status_code == 500

    response = server_error(request, template_name='non-existing.html')
    assert response.status_code == 500
