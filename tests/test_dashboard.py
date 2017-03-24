# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.utils import timezone

from atmo.clusters.models import Cluster
from atmo.jobs.models import SparkJob
from atmo.views import server_error


def make_spark_job(id, date, owner):
    identifier = 'test-spark-job-%s' % id
    job = SparkJob.objects.create(
        identifier=identifier,
        notebook_s3_key='jobs/%s/test-notebook-%s.ipynb' % (identifier, id),
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=date - timedelta(hours=2, minutes=id),
        created_by=owner,
    )
    job.runs.create(
        scheduled_date=date - timedelta(hours=1, minutes=id),
    )


def test_dashboard_jobs(client, test_user, test_user2):
    dashboard_url = reverse('dashboard')

    # Make some spark jobs owned by this user.
    for n in range(10):
        make_spark_job(n, timezone.now(), test_user)

    # Create extra jobs from another user so the test isn't so easy.
    for n in range(10, 15):
        make_spark_job(n, timezone.now(), test_user2)

    response = client.get(dashboard_url, follow=True)
    assert 'spark_jobs' in response.context
    assert response.context['spark_jobs'].count() == 10

    # A non-group user gets redirected.
    response2 = client.get(dashboard_url + '?jobs=all', follow=True)
    assert response2.redirect_chain[-1] == (dashboard_url, 302)

    # Add user to the spark job maintainer group.
    group, _ = Group.objects.get_or_create(name='Spark job maintainers')
    group.user_set.add(test_user)

    response3 = client.get(dashboard_url + '?jobs=all', follow=True)
    assert 'spark_jobs' in response3.context
    assert response3.context['spark_jobs'].count() == 15

    response4 = client.get(dashboard_url + '?jobs=foobar', follow=True)
    assert 'spark_jobs' in response4.context
    assert response4.context['spark_jobs'].count() == 10

    assert (set(response.context['spark_jobs'].values_list('pk', flat=True)) ==
            set(response4.context['spark_jobs'].values_list('pk', flat=True)))


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
            'state_change_reason_code': None,
            'state_change_reason_message': None,
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
