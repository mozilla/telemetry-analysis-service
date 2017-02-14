# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import io
from datetime import datetime, timedelta

import pytest
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.utils import timezone
from freezegun import freeze_time

from atmo.clusters.models import Cluster
from atmo.jobs import models


@pytest.fixture
def cluster_provisioner_mocks(mocker):
    return {
        'stop': mocker.patch(
            'atmo.clusters.provisioners.ClusterProvisioner.stop',
            return_value=None,
        ),
    }


@pytest.fixture
def sparkjob_provisioner_mocks(mocker):
    return {
        'get': mocker.patch(
            'atmo.jobs.provisioners.SparkJobProvisioner.get',
            return_value={
                'Body': io.BytesIO('content'),
                'ContentLength': 7,
            }
        ),
        'add': mocker.patch(
            'atmo.jobs.provisioners.SparkJobProvisioner.add',
            return_value=u'jobs/test-spark-job/test-notebook.ipynb',
        ),
        'results': mocker.patch(
            'atmo.jobs.provisioners.SparkJobProvisioner.results',
            return_value={},
        ),
        'run': mocker.patch(
            'atmo.jobs.provisioners.SparkJobProvisioner.run',
            return_value=u'12345',
        ),
        'remove': mocker.patch(
            'atmo.jobs.provisioners.SparkJobProvisioner.remove',
            return_value=None,
        ),
    }


def test_new_spark_job(client, test_user):
    response = client.get(reverse('jobs-new'))
    assert response.status_code == 200
    assert 'form' in response.context


def test_create_spark_job(client, mocker, notebook_maker,
                          spark_job_provisioner, test_user,
                          sparkjob_provisioner_mocks):

    mocker.patch.object(
        spark_job_provisioner.s3,
        'list_objects_v2',
        return_value={},
    )
    new_data = {
        'new-notebook': notebook_maker(),
        'new-description': 'A description',
        'new-notebook-cache': 'some-random-hash',
        'new-result_visibility': 'private',
        'new-size': 5,
        'new-interval_in_hours': 24,
        'new-job_timeout': 12,
        'new-start_date': '2016-04-05 13:25:47',
        'new-emr_release': models.SparkJob.EMR_RELEASES_CHOICES_DEFAULT,
    }

    response = client.post(reverse('jobs-new'), new_data, follow=True)
    assert not models.SparkJob.objects.filter(identifier='test-spark-job').exists()
    assert response.status_code == 200
    assert response.context['form'].errors

    new_data.update({
        'new-identifier': 'test-spark-job',  # add required data
        'new-notebook': notebook_maker(extension='foo'),  # but add a bad file
    })
    response = client.post(reverse('jobs-new'), new_data, follow=True)
    assert not models.SparkJob.objects.filter(identifier='test-spark-job').exists()
    assert response.status_code == 200
    assert 'notebook' in response.context['form'].errors

    new_data.update({
        'new-identifier': 'test-spark-job',  # add required data
        'new-notebook': notebook_maker(),  # old file is exhausted
    })
    response = client.post(reverse('jobs-new'), new_data, follow=True)

    spark_job = models.SparkJob.objects.get(identifier='test-spark-job')

    assert repr(spark_job) == '<SparkJob test-spark-job with 5 nodes>'
    assert spark_job.get_info() is None
    assert spark_job.is_runnable
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.get_absolute_url(), 302)

    sparkjob_provisioner_mocks['add'].assert_called_once()
    kwargs = sparkjob_provisioner_mocks['add'].call_args[1]
    assert kwargs['identifier'] == 'test-spark-job'
    assert kwargs['notebook_file'].name == 'test-notebook.ipynb'

    assert spark_job.identifier == 'test-spark-job'
    assert spark_job.description == 'A description'
    assert spark_job.notebook_s3_key == u'jobs/test-spark-job/test-notebook.ipynb'
    assert spark_job.result_visibility == 'private'
    assert spark_job.size == 5
    assert spark_job.interval_in_hours == 24
    assert spark_job.job_timeout == 12
    assert (
        spark_job.start_date ==
        timezone.make_aware(datetime(2016, 4, 5, 13, 25, 47))
    )
    assert spark_job.end_date is None
    assert spark_job.created_by == test_user

    mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.info',
        return_value={
            'start_time': timezone.now(),
            'state': Cluster.STATUS_BOOTSTRAPPING,
            'public_dns': None,
        },
    )
    sparkjob_provisioner_mocks['run'].assert_not_called()
    spark_job.run()
    sparkjob_provisioner_mocks['run'].assert_called_once_with(
        emr_release=models.SparkJob.EMR_RELEASES_CHOICES_DEFAULT,
        identifier=spark_job.identifier,
        is_public=False,
        job_timeout=spark_job.job_timeout,
        notebook_key=spark_job.notebook_s3_key,
        size=spark_job.size,
        user_email=test_user.email,
    )

    response = client.get(spark_job.get_absolute_url() + '?render=true', follow=True)
    assert response.status_code == 200
    assert 'notebook_content' in response.context

    assert not spark_job.should_run()


@pytest.mark.django_db
@freeze_time('2016-04-05 13:25:47')
def test_edit_spark_job(request, mocker, client, test_user, test_user2,
                        sparkjob_provisioner_mocks):

    now = timezone.now()
    now_string = now.strftime('%Y-%m-%d %H:%M:%S')
    one_hour_ago = now - timedelta(hours=1)
    one_hour_from_now = now + timedelta(hours=1)

    # create a test job to edit later
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job',
        description='description',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now,
        created_by=test_user,
        last_run_date=one_hour_ago
    )

    edit_url = reverse('jobs-edit', kwargs={'id': spark_job.id})

    response = client.get(edit_url)
    assert response.status_code == 200
    assert 'form' in response.context
    assert 'Current notebook' in response.content

    # login the second user so we can check the change_sparkjob permission
    client.force_login(test_user2)
    response = client.get(edit_url, follow=True)
    assert response.status_code == 403
    client.force_login(test_user)

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
    assert response.redirect_chain[-1] == (spark_job.get_absolute_url(), 302)

    # changing identifier isn't allowed
    assert spark_job.identifier != 'new-spark-job-name'
    assert spark_job.description == 'New description'
    assert spark_job.notebook_s3_key == u'jobs/test-spark-job/test-notebook.ipynb'
    assert spark_job.result_visibility == 'public'
    assert spark_job.size == 3
    assert spark_job.interval_in_hours == 24 * 7
    assert spark_job.job_timeout == 10
    assert spark_job.start_date == now
    assert spark_job.end_date is None
    assert spark_job.created_by == test_user
    assert spark_job.last_run_date == one_hour_ago

    edit_data['edit-start_date'] = one_hour_from_now.strftime('%Y-%m-%d %H:%M:%S')

    response = client.post(edit_url, edit_data, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.get_absolute_url(), 302)

    spark_job.refresh_from_db()
    # Moving the start_date to a future date should reset the last_run_date
    assert spark_job.last_run_date is None

    edit_data['edit-start_date'] = one_hour_ago.strftime('%Y-%m-%d %H:%M:%S')

    response = client.post(edit_url, edit_data, follow=True)
    # Moving the start_date to a past date should not be allowed
    assert response.status_code == 200
    assert 'form' in response.context
    assert response.context['form'].errors


def test_delete_spark_job(request, mocker, client, test_user, test_user2, sparkjob_provisioner_mocks):

    # create a test job to delete later
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job',
        description='description',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=timezone.make_aware(datetime(2016, 4, 5, 13, 25, 47)),
        created_by=test_user,
    )
    delete_url = reverse('jobs-delete', kwargs={'id': spark_job.id})

    response = client.get(delete_url)
    assert response.status_code == 200

    # login the second user so we can check the delete_sparkjob permission
    client.force_login(test_user2)
    response = client.get(delete_url, follow=True)
    assert response.status_code == 403
    client.force_login(test_user)

    # request that the test job be deleted
    response = client.post(delete_url, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1], ('/' == 302)

    sparkjob_provisioner_mocks['remove'].assert_called_with(
        'jobs/test-spark-job/test-notebook.ipynb'
    )
    assert (
        not models.SparkJob.objects.filter(identifier=u'test-spark-job').exists()
    )


def test_download(client, mocker, now, test_user, test_user2, sparkjob_provisioner_mocks):
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job',
        description='description',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now - timedelta(hours=1),
        created_by=test_user,
    )
    download_url = reverse('jobs-download', kwargs={'id': spark_job.id})

    # login the second user so we can check the view_sparkjob permission
    client.force_login(test_user2)
    response = client.get(download_url, follow=True)
    assert response.status_code == 403
    client.force_login(test_user)

    response = client.get(download_url)
    assert response.status_code == 200
    assert response['Content-Length'] == '7'
    assert 'test-notebook.ipynb' in response['Content-Disposition']

    # getting the file for a non-existing job returns a 404
    response = client.get(reverse('jobs-download', kwargs={'id': 42}))
    assert response.status_code == 404


def test_spark_job_first_run_should_run(now, test_user):
    spark_job_first_run = models.SparkJob.objects.create(
        identifier='test-spark-job',
        description='description',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now - timedelta(hours=1),
        created_by=test_user,
    )
    assert spark_job_first_run.has_never_run
    assert not spark_job_first_run.has_finished
    assert spark_job_first_run.is_runnable
    assert spark_job_first_run.should_run()


def test_spark_job_not_active_should_run(now, test_user):
    spark_job_not_active = models.SparkJob.objects.create(
        identifier='test-spark-job-2',
        description='description',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now + timedelta(hours=1),
        created_by=test_user
    )
    assert not spark_job_not_active.should_run()


def test_spark_job_expired_should_run(mocker, now, test_user):
    mocker.patch(
        'django.utils.timezone.now',
        return_value=now + timedelta(seconds=1)
    )
    spark_job_expired = models.SparkJob.objects.create(
        identifier='test-spark-job-3',
        description='description',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now - timedelta(hours=1),
        end_date=now,
        created_by=test_user,
    )
    assert not spark_job_expired.should_run()


def test_spark_job_not_ready_should_run(now, test_user):
    spark_job_not_ready = models.SparkJob.objects.create(
        identifier='test-spark-job-4',
        description='description',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now - timedelta(hours=2),
        last_run_date=now - timedelta(hours=1),
        created_by=test_user,
    )
    assert not spark_job_not_ready.should_run()


def test_spark_job_second_run_should_run(now, test_user):
    spark_job_second_run = models.SparkJob.objects.create(
        identifier='test-spark-job-5',
        description='description',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=1,
        job_timeout=12,
        start_date=now - timedelta(days=1),
        last_run_date=now - timedelta(hours=2),
        created_by=test_user,
        most_recent_status=Cluster.STATUS_TERMINATED,
    )
    assert spark_job_second_run.should_run()


def test_spark_job_is_expired(now, test_user):
    # Test that a spark job `is_expired` if it has run for longer than
    # its timeout.
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job-6',
        description='description',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=1,
        job_timeout=12,
        start_date=now - timedelta(days=1),
        created_by=test_user,
        current_run_jobflow_id='my-jobflow-id',
    )

    timeout_run_date = now - timedelta(hours=12)
    running_status = Cluster.STATUS_RUNNING

    # No last_run_date and no status
    spark_job.last_run_date = None
    spark_job.most_recent_status = ''
    assert not spark_job.is_expired

    # No last_run_date and running status
    spark_job.last_run_date = None
    spark_job.most_recent_status = running_status
    assert not spark_job.is_expired

    # Most_recent_status != RUNNING
    spark_job.last_run_date = timeout_run_date
    spark_job.most_recent_status = Cluster.STATUS_TERMINATED
    assert not spark_job.is_expired

    # It hasn't run for more than its timeout
    spark_job.last_run_date = timeout_run_date + timedelta(seconds=1)
    spark_job.most_recent_status = running_status
    assert not spark_job.is_expired

    # All the conditions are met
    spark_job.last_run_date = timeout_run_date
    spark_job.most_recent_status = running_status
    assert spark_job.is_expired


def test_spark_job_terminates(now, test_user, cluster_provisioner_mocks):
    # Test that a spark job's `terminate` tells the EMR to terminate correctly.
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job-7',
        description='description',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=1,
        job_timeout=12,
        start_date=now - timedelta(days=1),
        created_by=test_user,
        current_run_jobflow_id='jobflow-id',
    )

    timeout_run_date = now - timedelta(hours=12)
    running_status = Cluster.STATUS_RUNNING

    # Test job does not terminate if not expired.
    spark_job.last_run_date = timeout_run_date + timedelta(seconds=1)
    spark_job.most_recent_status = running_status
    spark_job.terminate()
    cluster_provisioner_mocks['stop'].assert_not_called()

    # Test job terminates when expired.
    spark_job.last_run_date = timeout_run_date
    spark_job.most_recent_status = running_status
    spark_job.terminate()
    cluster_provisioner_mocks['stop'].assert_called_with(u'jobflow-id')


def test_check_identifier_available(client, test_user):
    # create a test job to edit later
    identifier = 'test-spark-job'
    spark_job = models.SparkJob.objects.create(
        identifier=identifier,
        description='description',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=timezone.make_aware(datetime(2016, 4, 5, 13, 25, 47)),
        created_by=test_user,
    )
    available_url = reverse('jobs-identifier-available')

    response = client.get(available_url)
    assert response.status_code == 404
    assert 'identifier invalid' in response.content

    response = client.get(available_url + '?identifier=%s' % identifier)
    assert 'identifier unavailable' in response.content

    response = client.get(available_url + '?identifier=completely-different')
    assert 'identifier available' in response.content

    response = client.get(
        available_url +
        '?identifier=%s&id=%s' % (identifier, spark_job.id)
    )
    assert 'identifier available' in response.content
