# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import io
import pytest
from datetime import datetime, timedelta
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.utils import timezone
from django.utils.text import get_valid_filename

from atmo.jobs import models


def make_test_notebook(extension='ipynb'):
    return InMemoryUploadedFile(
        file=io.BytesIO('{}'),
        field_name='notebook',
        name='test-notebook.%s' % extension,
        content_type='text/plain',
        size=2,
        charset='utf8',
    )


def test_new_spark_job(client, test_user):
    response = client.get(reverse('jobs-new'))
    assert response.status_code == 200
    assert 'form' in response.context


def test_create_spark_job(mocker, monkeypatch, client, test_user):
    mocker.patch('atmo.scheduling.spark_job_get', return_value={
        'Body': io.BytesIO('content'),
        'ContentLength': 7,
    })
    mock_spark_job_add = mocker.patch(
        'atmo.scheduling.spark_job_add',
        return_value=u's3://test/test-notebook.ipynb',
    )
    new_data = {
        'new-notebook': make_test_notebook(),
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
        'new-notebook': make_test_notebook(extension='foo'),  # but add a bad file
    })
    response = client.post(reverse('jobs-new'), new_data, follow=True)
    assert not models.SparkJob.objects.filter(identifier='test-spark-job').exists()
    assert response.status_code == 200
    assert 'notebook' in response.context['form'].errors

    new_data.update({
        'new-identifier': 'test-spark-job',  # add required data
        'new-notebook': make_test_notebook(),  # old file is exhausted
    })
    response = client.post(reverse('jobs-new'), new_data, follow=True)

    spark_job = models.SparkJob.objects.get(identifier='test-spark-job')

    assert repr(spark_job) == '<SparkJob test-spark-job with 5 nodes>'

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


@pytest.mark.django_db
def test_edit_spark_job(request, mocker, client, test_user):
    mocker.patch('atmo.scheduling.spark_job_run', return_value=u'12345')
    mocker.patch('atmo.scheduling.spark_job_get', return_value={
        'Body': io.BytesIO('content'),
        'ContentLength': 7,
    })

    # create a test job to edit later
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job',
        notebook_s3_key=u's3://test/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=timezone.make_aware(datetime(2016, 4, 5, 13, 25, 47)),
        created_by=test_user,
    )

    edit_url = reverse('jobs-edit', kwargs={'id': spark_job.id})

    response = client.get(edit_url)
    assert response.status_code == 200
    assert 'form' in response.context

    edit_data = {
        'edit-job': spark_job.id,
        'edit-identifier': 'new-spark-job-name',
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

    edit_data['edit-start_date'] = '2016-03-08 11:17:35'  # fix the date
    response = client.post(edit_url, edit_data, follow=True)

    spark_job.refresh_from_db()
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.get_absolute_url(), 302)

    # changing identifier isn't allowed
    assert spark_job.identifier != 'new-spark-job-name'
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
    spark_job_remove = mocker.patch(
        'atmo.scheduling.spark_job_remove',
        return_value=None,
    )
    mocker.patch('atmo.scheduling.spark_job_get', return_value={
        'Body': 'content',
        'ContentLength': 7,
    })

    # create a test job to delete later
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job',
        notebook_s3_key=u's3://test/test-notebook.ipynb',
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
    assert 'Confirm deletion' in response.content

    # request that the test job be deleted, with the wrong confirmation
    response = client.post(delete_url, {
        'delete-job': spark_job.id,
        'delete-confirmation': 'definitely-not-the-correct-identifier',
    }, follow=True)

    assert models.SparkJob.objects.filter(pk=spark_job.pk).exists()  # not deleted
    assert spark_job_remove.call_count == 0  # and also not removed from S3
    assert 'Entered Spark job identifier' in response.content

    # request that the test job be deleted, with the correct confirmation
    response = client.post(delete_url, {
        'delete-job': spark_job.id,
        'delete-confirmation': spark_job.identifier,
    }, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1], ('/' == 302)

    assert spark_job_remove.call_count == 1
    (notebook_s3_key,) = spark_job_remove.call_args[0]
    assert notebook_s3_key == u's3://test/test-notebook.ipynb'

    assert (
        not models.SparkJob.objects.filter(identifier=u'test-spark-job').exists()
    )
    assert django_user_model.objects.filter(username='john.smith').exists()


def test_download(client, mocker, now, test_user):
    mocker.patch('atmo.scheduling.spark_job_get', return_value={
        'Body': io.BytesIO('content'),
        'ContentLength': 7,
    })
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job',
        notebook_s3_key=u's3://test/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now - timedelta(hours=1),
        created_by=test_user,
    )
    response = client.get(reverse('jobs-download', kwargs={'id': spark_job.id}))
    assert response.status_code == 200
    assert response['Content-Length'] == '7'
    assert 'test-notebook.ipynb' in response['Content-Disposition']


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


def test_check_identifier_taken(client, test_user):
    # create a test job to edit later
    identifier = 'test-spark-job'
    spark_job = models.SparkJob.objects.create(
        identifier=identifier,
        notebook_s3_key=u's3://test/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=timezone.make_aware(datetime(2016, 4, 5, 13, 25, 47)),
        created_by=test_user,
    )
    taken_url = reverse('jobs-identifier-taken')
    response = client.get(taken_url)

    assert isinstance(response, JsonResponse)
    assert 'No identifier provided' in response.content

    response = client.get(taken_url + '?identifier=%s' % identifier)
    assert 'Identifier is taken' in response.content
    assert 'alternative' in response.content
    assert identifier + '-2' in response.content  # the calculated alternative

    response = client.get(taken_url + '?identifier=completely-different')
    assert 'Identifier is available' in response.content

    response = client.get(taken_url + '?identifier=%s&id=%s' %
                                      (identifier, spark_job.id))
    assert 'Identifier is available' in response.content
