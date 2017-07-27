# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime, timedelta

import pytest
from botocore.exceptions import ClientError
from django.core.urlresolvers import reverse
from django.utils import timezone
from freezegun import freeze_time

from atmo.clusters.models import Cluster
from atmo.jobs import models


def test_new_spark_job(client):
    response = client.get(reverse('jobs-new'))
    assert response.status_code == 200
    assert 'form' in response.context


@pytest.mark.usefixtures('transactional_db')
def test_create_spark_job(client, mocker, emr_release, notebook_maker,
                          spark_job_provisioner, user,
                          sparkjob_provisioner_mocks):

    mocker.patch.object(
        spark_job_provisioner.s3,
        'list_objects_v2',
        return_value={},
    )
    new_data = {
        'new-identifier': 'test-spark-job',
        'new-notebook': notebook_maker(),
        'new-description': 'A description',
        'new-notebook-cache': 'some-random-hash',
        'new-result_visibility': 'private',
        'new-size': 5,
        'new-interval_in_hours': 24,
        'new-job_timeout': 12,
        'new-start_date': '2016-04-05 13:25:47',
        'new-emr_release': emr_release.version,
    }

    response = client.post(reverse('jobs-new'), new_data, follow=True)

    spark_job = models.SparkJob.objects.get(identifier='test-spark-job')

    assert (
        "<atmo.jobs.models.SparkJob identifier='test-spark-job' size=5 is_enabled=True"
        in
        repr(spark_job)
    )
    assert spark_job.latest_run is None
    assert spark_job.is_runnable
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.urls.detail, 302)

    sparkjob_provisioner_mocks['add'].call_count == 1
    kwargs = sparkjob_provisioner_mocks['add'].call_args[1]
    assert kwargs['identifier'] == 'test-spark-job'
    assert kwargs['notebook_file'].name == 'test-notebook.ipynb'

    assert spark_job.identifier == 'test-spark-job'
    assert spark_job.description == 'A description'
    assert spark_job.notebook_s3_key == 'jobs/test-spark-job/test-notebook.ipynb'
    assert spark_job.result_visibility == 'private'
    assert spark_job.size == 5
    assert spark_job.interval_in_hours == 24
    assert spark_job.job_timeout == 12
    assert (
        spark_job.start_date ==
        timezone.make_aware(datetime(2016, 4, 5, 13, 25, 47))
    )
    assert spark_job.end_date is None
    assert spark_job.created_by == user

    mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.info',
        return_value={
            'creation_datetime': timezone.now(),
            'ready_datetime': None,
            'end_datetime': None,
            'state': Cluster.STATUS_BOOTSTRAPPING,
            'state_change_reason_code': None,
            'state_change_reason_message': None,
            'public_dns': None,
        },
    )
    sparkjob_provisioner_mocks['run'].assert_not_called()
    spark_job.run()
    sparkjob_provisioner_mocks['run'].assert_called_once_with(
        emr_release=emr_release.version,
        identifier=spark_job.identifier,
        is_public=False,
        job_timeout=spark_job.job_timeout,
        notebook_key=spark_job.notebook_s3_key,
        size=spark_job.size,
        user_email=user.email,
        user_username=user.username,
    )
    assert spark_job.latest_run is not None
    assert spark_job.latest_run.status == Cluster.STATUS_BOOTSTRAPPING
    assert not spark_job.should_run
    assert str(spark_job.latest_run) == '12345'
    assert (
        "<atmo.jobs.models.SparkJob identifier='test-spark-job' size=5 is_enabled=True"
        in
        repr(spark_job)
    )
    # just a thing autorepr needs
    assert (
        spark_job.latest_run.spark_job_identifier() ==
        spark_job.identifier
    )

    # forcibly resetting the cached_property latest_run
    old_latest_run = spark_job.latest_run
    del spark_job.latest_run
    assert not spark_job.is_runnable
    spark_job.run()
    assert old_latest_run == spark_job.latest_run

    spark_job.latest_run.status = Cluster.STATUS_TERMINATED
    spark_job.latest_run.save()
    del spark_job.latest_run
    assert spark_job.is_runnable
    del spark_job.latest_run
    spark_job.run()
    assert old_latest_run != spark_job.latest_run


@freeze_time('2016-04-05 13:25:47')
def test_edit_spark_job(request, mocker, client, user, user2,
                        sparkjob_provisioner_mocks, spark_job_with_run_factory):

    now = timezone.now()
    now_string = now.strftime('%Y-%m-%d %H:%M:%S')
    one_hour_ago = now - timedelta(hours=1)

    # create a test job to edit later
    spark_job = spark_job_with_run_factory(
        start_date=now,
        created_by=user,
        run__scheduled_at=one_hour_ago,
    )

    edit_url = reverse('jobs-edit', kwargs={'id': spark_job.id})

    response = client.get(edit_url)
    assert response.status_code == 200
    assert 'form' in response.context
    assert b'Current notebook' in response.content

    # login the second user so we can check the change_sparkjob permission
    client.force_login(user2)
    response = client.get(edit_url, follow=True)
    assert response.status_code == 403
    client.force_login(user)

    edit_data = {
        'edit-job': spark_job.id,
        'edit-identifier': 'new-spark-job-name',
        'edit-description': 'New description',
        'edit-result_visibility': 'public',
        'edit-notebook-cache': 'some-random-hash',
        'edit-size': 3,
        'edit-interval_in_hours': 24 * 7,
        'edit-job_timeout': 10,
        'edit-start_date': 'some-wonky-start-date',  # broken data
    }

    response = client.post(edit_url, edit_data, follow=True)
    assert response.status_code == 200
    assert 'form' in response.context
    assert response.context['form'].errors

    edit_data['edit-start_date'] = now_string
    response = client.post(edit_url, edit_data, follow=True)

    spark_job.refresh_from_db()
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.urls.detail, 302)

    # changing identifier isn't allowed
    assert spark_job.identifier != 'new-spark-job-name'
    assert spark_job.description == 'New description'
    assert spark_job.result_visibility == 'public'
    assert spark_job.size == 3
    assert spark_job.interval_in_hours == 24 * 7
    assert spark_job.job_timeout == 10
    assert spark_job.start_date == now
    assert spark_job.end_date is None
    assert spark_job.created_by == user
    assert spark_job.latest_run.scheduled_at == one_hour_ago

    edit_data['edit-start_date'] = one_hour_ago.strftime('%Y-%m-%d %H:%M:%S')

    response = client.post(edit_url, edit_data, follow=True)
    # Moving the start_date to a past date should not be allowed
    assert response.status_code == 200
    assert 'form' in response.context
    assert response.context['form'].errors


@freeze_time('2016-04-05 13:25:47')
def test_delete_spark_job(request, mocker, client, user, user2,
                          sparkjob_provisioner_mocks,
                          cluster_provisioner_mocks,
                          spark_job_with_run_factory,
                          emr_release):
    # create a test job to delete later
    spark_job = spark_job_with_run_factory(
        created_by=user,
        emr_release=emr_release,
    )
    delete_url = reverse('jobs-delete', kwargs={'id': spark_job.id})

    response = client.get(delete_url)
    assert response.status_code == 200

    # login the second user so we can check the delete_sparkjob permission
    client.force_login(user2)
    response = client.get(delete_url, follow=True)
    assert response.status_code == 403
    client.force_login(user)

    jobflow_id = spark_job.latest_run.jobflow_id

    # request that the test job be deleted
    response = client.post(delete_url, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1], ('/' == 302)

    # Spark job notebook was deleted
    sparkjob_provisioner_mocks['remove'].assert_called_with(spark_job.notebook_s3_key)
    cluster_provisioner_mocks['stop'].assert_called_with(jobflow_id)
    # and also removed from the database
    assert not models.SparkJob.objects.filter(pk=spark_job.pk).exists()


def test_download(client, mocker, now, one_hour_ago, user, user2,
                  sparkjob_provisioner_mocks,
                  spark_job_with_run_factory, emr_release):
    spark_job = spark_job_with_run_factory(
        start_date=one_hour_ago,
        created_by=user,
        emr_release=emr_release,
    )
    download_url = reverse('jobs-download', kwargs={'id': spark_job.id})

    # login the second user so we can check the view_sparkjob permission
    client.force_login(user2)
    response = client.get(download_url, follow=True)
    assert response.status_code == 403
    client.force_login(user)

    response = client.get(download_url)
    assert response.status_code == 200
    assert response['Content-Length'] == '7'
    assert spark_job.notebook_name in response['Content-Disposition']

    # getting the file for a non-existing job returns a 404
    response = client.get(reverse('jobs-download', kwargs={'id': 42}))
    assert response.status_code == 404


@freeze_time('2016-04-05 13:25:47')
def test_check_identifier_available(client, spark_job):
    # create a test job to edit later
    available_url = reverse('jobs-identifier-available')

    response = client.get(available_url)
    assert response.status_code == 404
    assert b'identifier invalid' in response.content

    response = client.get(available_url + '?identifier=%s' % spark_job.identifier)
    assert b'identifier unavailable' in response.content

    response = client.get(available_url + '?identifier=completely-different')
    assert b'identifier available' in response.content


def test_run_without_latest_run(client, messages, mocker, one_hour_ago, spark_job):
    run = mocker.patch('atmo.jobs.models.SparkJob.run')
    sync = mocker.patch('atmo.jobs.models.SparkJobRun.sync')
    mocker.patch(
        'atmo.jobs.models.SparkJob.results',
        new_callable=mocker.PropertyMock,
        return_valurn=[],
    )
    assert spark_job.is_runnable
    response = client.get(spark_job.urls.run, follow=True)
    assert response.status_code == 200
    assert not response.redirect_chain
    assert run.call_count == 0
    assert sync.call_count == 0

    response = client.post(spark_job.urls.run, follow=True)
    assert run.call_count == 1
    assert sync.call_count == 0
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.urls.detail, 302)


def test_run_with_latest_run(client, messages, mocker, one_hour_ago, spark_job):
    run = mocker.patch('atmo.jobs.models.SparkJob.run')
    sync = mocker.patch('atmo.jobs.models.SparkJobRun.sync')
    mocker.patch(
        'atmo.jobs.models.SparkJob.results',
        new_callable=mocker.PropertyMock,
        return_valurn=[],
    )
    spark_job.runs.create(
        jobflow_id='my-jobflow-id',
        status=Cluster.STATUS_TERMINATED,
        scheduled_at=one_hour_ago,
    )
    assert spark_job.is_runnable
    response = client.get(spark_job.urls.run, follow=True)
    assert response.status_code == 200
    assert not response.redirect_chain
    assert run.call_count == 0
    assert sync.call_count == 0

    response = client.post(spark_job.urls.run, follow=True)
    assert run.call_count == 1
    assert sync.call_count == 1
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.urls.detail, 302)


def test_run_with_client_error(client, messages, mocker, one_hour_ago, spark_job):
    run = mocker.patch('atmo.jobs.models.SparkJob.run')
    sync = mocker.patch(
        'atmo.jobs.models.SparkJobRun.sync',
        side_effect=ClientError({
            'Error': {
                'Code': 'Code',
                'Message': 'Message',
            }
        }, 'operation_name'),
    )
    mocker.patch(
        'atmo.jobs.models.SparkJob.results',
        new_callable=mocker.PropertyMock,
        return_valurn=[],
    )
    spark_job.runs.create(
        jobflow_id='my-jobflow-id',
        status=Cluster.STATUS_TERMINATED,
        scheduled_at=one_hour_ago,
    )
    response = client.post(spark_job.urls.run, follow=True)
    assert run.call_count == 0
    assert sync.call_count == 1
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.urls.detail, 302)
    messages.assert_message_contains(response, 'Spark job API error')


def test_run_not_runnable(client, messages, mocker, now, spark_job):
    results = mocker.patch(
        'atmo.jobs.models.SparkJob.results',
        new_callable=mocker.PropertyMock,
        return_valurn=[],
    )
    spark_job.runs.create(
        jobflow_id='my-jobflow-id',
        status=Cluster.STATUS_RUNNING,
        scheduled_at=now,
    )
    assert not spark_job.is_runnable
    response = client.post(spark_job.urls.run, follow=True)
    assert response.redirect_chain[-1] == (spark_job.urls.detail, 302)
    messages.assert_message_contains(response, 'Run now unavailable')
    assert results.call_count == 2
