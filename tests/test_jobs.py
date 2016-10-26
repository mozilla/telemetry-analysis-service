# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import io
import pytest
from datetime import datetime, timedelta
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.urlresolvers import reverse
from django.utils import timezone

from atmo.jobs import models


def make_test_notebook():
    return InMemoryUploadedFile(
        file=io.BytesIO('{}'),
        field_name='notebook',
        name='test-notebook.ipynb',
        content_type='text/plain',
        size=2,
        charset='utf8',
    )


def test_create_spark_job(mocker, monkeypatch, client, test_user):
    mocker.patch(
        'atmo.scheduling.spark_job_get',
        return_value=u'content',
    )
    mock_spark_job_add = mocker.patch(
        'atmo.scheduling.spark_job_add',
        return_value=u's3://test/test-notebook.ipynb',
    )
    response = client.post(reverse('jobs-new'), {
        'new-identifier': 'test-spark-job',
        'new-notebook': make_test_notebook(),
        'new-notebook-cache': 'some-random-hash',
        'new-result_visibility': 'private',
        'new-size': 5,
        'new-interval_in_hours': 24,
        'new-job_timeout': 12,
        'new-start_date': '2016-04-05 13:25:47',
        'new-emr_release': models.SparkJob.EMR_RELEASES_CHOICES_DEFAULT,
    }, follow=True)

    spark_job = models.SparkJob.objects.get(identifier='test-spark-job')

    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.get_absolute_url(), 302)

    assert mock_spark_job_add.call_count == 1
    identifier, notebook_uploadedfile = mock_spark_job_add.call_args[0]
    assert identifier == u'test-spark-job'
    assert notebook_uploadedfile.name == 'test-notebook.ipynb'

    assert spark_job.identifier == 'test-spark-job'
    assert spark_job.notebook_s3_key == u's3://test/test-notebook.ipynb'
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

    mock_spark_job_run = mocker.patch(
        'atmo.scheduling.spark_job_run',
        return_value=u'12345',
    )
    mocker.patch(
        'atmo.provisioning.cluster_info',
        return_value={
            'start_time': timezone.now(),
            'state': 'BOOTSTRAPPING',
            'public_dns': None,
        },
    )
    assert mock_spark_job_run.call_count == 0
    spark_job.run()
    assert mock_spark_job_run.call_count == 1
    user_email, identifier, notebook_uri, result_is_public, size, \
        job_timeout, emr_release = mock_spark_job_run.call_args[0]
    assert emr_release == models.SparkJob.EMR_RELEASES_CHOICES_DEFAULT


@pytest.fixture
@pytest.mark.django_db
def test_edit_spark_job(request, mocker, client, test_user):
    mocker.patch('atmo.scheduling.spark_job_run', return_value=u'12345')
    mocker.patch('atmo.scheduling.spark_job_get', return_value=u'content')

    # create a test job to edit later
    spark_job = models.SparkJob(
        identifier='test-spark-job',
        notebook_s3_key=u's3://test/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=timezone.make_aware(datetime(2016, 4, 5, 13, 25, 47)),
        created_by=test_user,
    )
    spark_job.save()

    response = client.post(
        reverse('jobs-edit', kwargs={
            'id': spark_job.id,
        }), {
            'edit-job': spark_job.id,
            'edit-identifier': 'new-spark-job-name',
            'edit-result_visibility': 'public',
            'edit-notebook-cache': 'some-random-hash',
            'edit-size': 3,
            'edit-interval_in_hours': 24 * 7,
            'edit-job_timeout': 10,
            'edit-start_date': '2016-03-08 11:17:35',
        }, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.get_absolute_url(), 302)

    assert spark_job.identifier == 'new-spark-job-name'
    assert spark_job.notebook_s3_key == u's3://test/test-notebook.ipynb'
    assert spark_job.result_visibility == 'public'
    assert spark_job.size == 3
    assert spark_job.interval_in_hours == 24 * 7
    assert spark_job.job_timeout == 10
    assert (
        spark_job.start_date ==
        timezone.make_aware(datetime(2016, 3, 8, 11, 17, 35))
    )
    assert spark_job.end_date is None
    assert spark_job.created_by == test_user


def test_delete_spark_job(request, mocker, client, test_user, django_user_model):
    mocked_spark_job_remove = mocker.patch(
        'atmo.scheduling.spark_job_remove', return_value=None)
    mocker.patch('atmo.scheduling.spark_job_get', return_value=u'content')

    # create a test job to delete later
    spark_job = models.SparkJob()
    spark_job.identifier = 'test-spark-job'
    spark_job.notebook_s3_key = u's3://test/test-notebook.ipynb'
    spark_job.result_visibility = 'private'
    spark_job.size = 5
    spark_job.interval_in_hours = 24
    spark_job.job_timeout = 12
    spark_job.start_date = timezone.make_aware(datetime(2016, 4, 5, 13, 25, 47))
    spark_job.created_by = test_user
    spark_job.save()

    # request that the test job be deleted
    response = client.post(
        reverse('jobs-delete', kwargs={
            'id': spark_job.id,
        }), {
            'delete-job': spark_job.id,
            'delete-confirmation': spark_job.identifier,
        }, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1], ('/' == 302)

    assert mocked_spark_job_remove.call_count == 1
    (notebook_s3_key,) = mocked_spark_job_remove.call_args[0]
    assert notebook_s3_key == u's3://test/test-notebook.ipynb'

    assert (
        not models.SparkJob.objects.filter(identifier=u'test-spark-job').exists()
    )
    assert django_user_model.objects.filter(username='john.smith').exists()


def test_spark_job_first_run_should_run(now, test_user):
    spark_job_first_run = models.SparkJob.objects.create(
        identifier='test-spark-job',
        notebook_s3_key=u's3://test/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now - timedelta(hours=1),
        created_by=test_user,
    )
    assert spark_job_first_run.should_run(at_time=now)


def test_spark_job_not_active_should_run(now, test_user):
    spark_job_not_active = models.SparkJob.objects.create(
        identifier='test-spark-job-2',
        notebook_s3_key=u's3://test/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now + timedelta(hours=1),
        created_by=test_user
    )
    assert not spark_job_not_active.should_run(at_time=now)


def test_spark_job_expired_should_run(now, test_user):
    spark_job_expired = models.SparkJob.objects.create(
        identifier='test-spark-job-3',
        notebook_s3_key=u's3://test/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now - timedelta(hours=1),
        end_date=now,
        created_by=test_user,
    )
    assert not spark_job_expired.should_run(at_time=now + timedelta(seconds=1))


def test_spark_job_not_ready_should_run(now, test_user):
    spark_job_not_ready = models.SparkJob.objects.create(
        identifier='test-spark-job-4',
        notebook_s3_key=u's3://test/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now - timedelta(hours=2),
        last_run_date=now - timedelta(hours=1),
        created_by=test_user,
    )
    assert not spark_job_not_ready.should_run(at_time=now)


def test_spark_job_second_run_should_run(now, test_user):
    spark_job_second_run = models.SparkJob.objects.create(
        identifier='test-spark-job-5',
        notebook_s3_key=u's3://test/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=1,
        job_timeout=12,
        start_date=now - timedelta(days=1),
        last_run_date=now - timedelta(hours=2),
        created_by=test_user,
    )
    assert spark_job_second_run.should_run(at_time=now)


def test_spark_job_is_expired(now, test_user):
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job-6',
        notebook_s3_key=u's3://test/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=1,
        job_timeout=12,
        start_date=now - timedelta(days=1),
        created_by=test_user,
    )
    # A spark job cannot expire if:
    # it doesn't have a jobflow_id OR
    # it doesn't have a a last_run_date OR
    # its most_recent_status is not RUNNING OR
    # it hasn't run for more than its timeout

    timeout_run_date = now - timedelta(hours=12)
    jobflow_id = 'my-jobflow-id'
    running_status = 'RUNNING'

    # No jobflow_id
    spark_job.current_run_jobflow_id = ''
    spark_job.last_run_date = timeout_run_date
    spark_job.most_recent_status = running_status
    assert not spark_job.is_expired(at_time=now)

    # No last_run_date
    spark_job.current_run_jobflow_id = jobflow_id
    spark_job.last_run_date = None
    spark_job.most_recent_status = running_status
    assert not spark_job.is_expired(at_time=now)

    # Most_recent_status != RUNNING
    spark_job.current_run_jobflow_id = jobflow_id
    spark_job.last_run_date = timeout_run_date
    spark_job.most_recent_status = "TERMINATED"
    assert not spark_job.is_expired(at_time=now)

    # It hasn't run for more than its timeout
    spark_job.current_run_jobflow_id = jobflow_id
    spark_job.last_run_date = timeout_run_date + timedelta(seconds=1)
    spark_job.most_recent_status = running_status
    assert not spark_job.is_expired(at_time=now)

    # All the conditions are met
    spark_job.current_run_jobflow_id = jobflow_id
    spark_job.last_run_date = timeout_run_date
    spark_job.most_recent_status = running_status
    assert spark_job.is_expired(at_time=now)

    # Default to now when not passing in a datetime
    spark_job.last_run_date = timeout_run_date - timedelta(seconds=5)
    assert spark_job.is_expired()
    spark_job.last_run_date = timeout_run_date + timedelta(seconds=5)
    assert not spark_job.is_expired()
