# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import io
import pytest
from datetime import datetime, timedelta
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.utils import timezone
from freezegun import freeze_time

from atmo.jobs import models
from atmo.clusters.models import Cluster


def test_new_spark_job(client, test_user):
    response = client.get(reverse('jobs-new'))
    assert response.status_code == 200
    assert 'form' in response.context


def test_create_spark_job(client, mocker, notebook_maker, test_user):
    mocker.patch('atmo.scheduling.spark_job_get', return_value={
        'Body': io.BytesIO('content'),
        'ContentLength': 7,
    })
    mock_spark_job_add = mocker.patch(
        'atmo.scheduling.spark_job_add',
        return_value=u'jobs/test-spark-job/test-notebook.ipynb',
    )
    mocker.patch('atmo.aws.s3.list_objects_v2', return_value={})
    new_data = {
        'new-notebook': notebook_maker(),
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

    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.get_absolute_url(), 302)

    assert mock_spark_job_add.call_count == 1
    identifier, notebook_uploadedfile = mock_spark_job_add.call_args[0]
    assert identifier == u'test-spark-job'
    assert notebook_uploadedfile.name == 'test-notebook.ipynb'

    assert spark_job.identifier == 'test-spark-job'
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

    mock_spark_job_run = mocker.patch(
        'atmo.scheduling.spark_job_run',
        return_value=u'12345',
    )
    mocker.patch(
        'atmo.provisioning.cluster_info',
        return_value={
            'start_time': timezone.now(),
            'state': Cluster.STATUS_BOOTSTRAPPING,
            'public_dns': None,
        },
    )
    assert mock_spark_job_run.call_count == 0
    spark_job.run()
    assert mock_spark_job_run.call_count == 1
    user_email, identifier, notebook_uri, result_is_public, size, \
        job_timeout, emr_release = mock_spark_job_run.call_args[0]
    assert emr_release == models.SparkJob.EMR_RELEASES_CHOICES_DEFAULT

    response = client.get(spark_job.get_absolute_url() + '?render=true', follow=True)
    assert response.status_code == 200
    assert 'notebook_content' in response.context


@pytest.mark.django_db
@freeze_time('2016-04-05 13:25:47')
def test_edit_spark_job(request, mocker, client, test_user):
    mocker.patch('atmo.scheduling.spark_job_run', return_value=u'12345')
    mocker.patch('atmo.scheduling.spark_job_get', return_value={
        'Body': io.BytesIO('content'),
        'ContentLength': 7,
    })
    mocker.patch('atmo.aws.s3.list_objects_v2', return_value={})

    now = timezone.now()
    now_string = now.strftime('%Y-%m-%d %H:%M:%S')
    one_hour_ago = now - timedelta(hours=1)
    one_hour_from_now = now + timedelta(hours=1)

    # create a test job to edit later
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job',
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

    edit_data['edit-start_date'] = now_string
    response = client.post(edit_url, edit_data, follow=True)

    spark_job.refresh_from_db()
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (spark_job.get_absolute_url(), 302)

    # changing identifier isn't allowed
    assert spark_job.identifier != 'new-spark-job-name'
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
    assert 'form' in response.context

    spark_job.refresh_from_db()
    # Moving the start_date to a future date should reset the last_run_date
    assert spark_job.last_run_date is None

    edit_data['edit-start_date'] = one_hour_ago.strftime('%Y-%m-%d %H:%M:%S')

    response = client.post(edit_url, edit_data, follow=True)
    # Moving the start_date to a past date should not be allowed
    assert response.status_code == 200
    assert 'form' in response.context
    assert response.context['form'].errors


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

    # request that the test job be deleted
    response = client.post(delete_url, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1], ('/' == 302)

    spark_job_remove.assert_called_with('jobs/test-spark-job/test-notebook.ipynb')
    assert (
        not models.SparkJob.objects.filter(identifier=u'test-spark-job').exists()
    )


def test_download(client, mocker, now, test_user):
    mocker.patch('atmo.scheduling.spark_job_get', return_value={
        'Body': io.BytesIO('content'),
        'ContentLength': 7,
    })
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=24,
        job_timeout=12,
        start_date=now - timedelta(hours=1),
        created_by=test_user,
    )
    download_url = reverse('jobs-download', kwargs={'id': spark_job.id})
    response = client.get(download_url)
    assert response.status_code == 200
    assert response['Content-Length'] == '7'
    assert 'test-notebook.ipynb' in response['Content-Disposition']

    # getting the file for a non-existing job returns a 404
    response = client.get(reverse('jobs-download', kwargs={'id': 42}))
    assert response.status_code == 404

    # getting the file if the S3 key is empty returns a 404
    spark_job.notebook_s3_key = ''
    spark_job.save()
    response = client.get(download_url)
    assert response.status_code == 404


def test_spark_job_first_run_should_run(now, test_user):
    spark_job_first_run = models.SparkJob.objects.create(
        identifier='test-spark-job',
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
    spark_job = models.SparkJob.objects.create(
        identifier='test-spark-job-6',
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
        result_visibility='private',
        size=5,
        interval_in_hours=1,
        job_timeout=12,
        start_date=now - timedelta(days=1),
        created_by=test_user,
        current_run_jobflow_id='my-jobflow-id',
    )
    # A spark job expires if:
    # or has run before and finished (or not)
    # it hasn't run for longer than its timeout

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


def test_check_identifier_taken(client, test_user):
    # create a test job to edit later
    identifier = 'test-spark-job'
    spark_job = models.SparkJob.objects.create(
        identifier=identifier,
        notebook_s3_key=u'jobs/test-spark-job/test-notebook.ipynb',
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
