# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from atmo.clusters.models import Cluster
from atmo.jobs import models


@pytest.mark.parametrize(
    # first is a regular pytest param, second is a pytest-factoryboy parameter
    'queryset_method,spark_job_run__status', [
        ['with_runs', models.DEFAULT_STATUS],
        ['active', Cluster.STATUS_STARTING],
        ['active', Cluster.STATUS_BOOTSTRAPPING],
        ['active', Cluster.STATUS_RUNNING],
        ['active', Cluster.STATUS_WAITING],
        ['active', Cluster.STATUS_TERMINATING],
        ['terminated', Cluster.STATUS_TERMINATED],
        ['failed', Cluster.STATUS_TERMINATED_WITH_ERRORS],
    ])
def test_various_querysets(queryset_method, spark_job_with_run):
    assert getattr(models.SparkJob.objects, queryset_method)().exists()


def test_lapsed_queryset(spark_job_factory, one_hour_ago):
    spark_job = spark_job_factory(
        end_date=one_hour_ago,
        expired_date=None,
    )
    assert spark_job in models.SparkJob.objects.lapsed()


@pytest.fixture
def update_status_factory(spark_job_with_run_factory, user):
    def factory():
        now = timezone.now()
        one_hour_ago = now - timedelta(hours=1)

        spark_job = spark_job_with_run_factory(
            start_date=now,
            created_by=user,
            run__status=models.DEFAULT_STATUS,
            run__scheduled_at=one_hour_ago,
        )
        return now, one_hour_ago, spark_job
    return factory


@freeze_time('2016-04-05 13:25:47')
def test_update_status_bootstrapping(request, mocker,
                                     sparkjob_provisioner_mocks,
                                     update_status_factory):

    now, one_hour_ago, spark_job = update_status_factory()

    mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.info',
        return_value={
            'creation_datetime': timezone.now(),
            'ready_datetime': None,
            'end_datetime': None,
            'state': Cluster.STATUS_BOOTSTRAPPING,
            'public_dns': None,
        },
    )
    spark_job.latest_run.update_status()
    assert spark_job.latest_run.status == Cluster.STATUS_BOOTSTRAPPING
    assert spark_job.latest_run.scheduled_at == one_hour_ago
    assert spark_job.latest_run.started_at is None
    assert spark_job.latest_run.ready_at is None
    assert spark_job.latest_run.finished_at is None


@freeze_time('2016-04-05 13:25:47')
def test_update_status_passed_info(request, mocker,
                                   sparkjob_provisioner_mocks,
                                   update_status_factory):

    now, one_hour_ago, spark_job = update_status_factory()

    mocker.spy(models.SparkJobRun, 'info')
    info = {
        'creation_datetime': timezone.now(),
        'ready_datetime': None,
        'end_datetime': None,
        'state': Cluster.STATUS_BOOTSTRAPPING,
        'public_dns': None,
    }
    provisioner_info = mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.info',
        return_value=info,
    )
    spark_job.latest_run.update_status(info=info)

    # info wasn't called since we're passing in the info ourselves
    assert spark_job.latest_run.info.call_count == 0
    # the provisioner wasn't called either of course
    assert provisioner_info.call_count == 0
    # just checking if the values are correct
    assert spark_job.latest_run.status == Cluster.STATUS_BOOTSTRAPPING
    assert spark_job.latest_run.scheduled_at == one_hour_ago
    assert spark_job.latest_run.started_at is None
    assert spark_job.latest_run.ready_at is None
    assert spark_job.latest_run.finished_at is None


@freeze_time('2016-04-05 13:25:47')
def test_update_status_running(request, mocker,
                               sparkjob_provisioner_mocks,
                               update_status_factory):

    now, one_hour_ago, spark_job = update_status_factory()

    mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.info',
        return_value={
            'creation_datetime': timezone.now(),
            'ready_datetime': None,
            'end_datetime': None,
            'state': Cluster.STATUS_RUNNING,
            'public_dns': None,
        },
    )
    spark_job.latest_run.update_status()
    assert spark_job.is_active
    assert spark_job.latest_run.status == Cluster.STATUS_RUNNING
    assert spark_job.latest_run.scheduled_at == one_hour_ago
    assert spark_job.latest_run.started_at == now
    assert spark_job.latest_run.ready_at is None
    assert spark_job.latest_run.finished_at is None

    # check again if the state hasn't changed
    spark_job.latest_run.update_status()
    assert spark_job.latest_run.status == Cluster.STATUS_RUNNING


@freeze_time('2016-04-05 13:25:47')
def test_update_status_terminated(request, mocker,
                                  sparkjob_provisioner_mocks,
                                  update_status_factory, one_hour_ago):

    now, one_hour_ago, spark_job = update_status_factory()

    mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.info',
        return_value={
            'creation_datetime': one_hour_ago,
            'ready_datetime': None,
            'end_datetime': now,
            'state': Cluster.STATUS_TERMINATED,
            'state_change_reason_code': Cluster.STATE_CHANGE_REASON_ALL_STEPS_COMPLETED,
            'state_change_reason_message': 'Steps completed',
            'public_dns': None,
        },
    )
    spark_job.latest_run.update_status()
    assert spark_job.latest_run.status == Cluster.STATUS_TERMINATED
    assert spark_job.latest_run.scheduled_at == one_hour_ago
    assert spark_job.latest_run.finished_at == now
    assert spark_job.latest_run.alert is None


@freeze_time('2016-04-05 13:25:47')
def test_update_status_terminated_with_errors(request, mocker,
                                              sparkjob_provisioner_mocks,
                                              update_status_factory):

    now, one_hour_ago, spark_job = update_status_factory()

    mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.info',
        return_value={
            'creation_datetime': timezone.now(),
            'ready_datetime': None,
            'end_datetime': None,
            'state': Cluster.STATUS_TERMINATED_WITH_ERRORS,
            'state_change_reason_code': Cluster.STATE_CHANGE_REASON_BOOTSTRAP_FAILURE,
            'state_change_reason_message': 'Bootstrapping steps failed.',
            'public_dns': None,
        },
    )
    spark_job.latest_run.update_status()
    assert spark_job.latest_run.alert is not None
    assert (spark_job.latest_run.alert.reason_code ==
            Cluster.STATE_CHANGE_REASON_BOOTSTRAP_FAILURE)
    assert spark_job.latest_run.alert.mail_sent_date is None
    assert spark_job.latest_run.status == Cluster.STATUS_TERMINATED_WITH_ERRORS


def test_first_run_without_run(mocker, spark_job):
    apply_async = mocker.patch('atmo.jobs.tasks.run_job.apply_async')
    spark_job.first_run()
    apply_async.assert_called_with(
        args=(spark_job.pk,),
        kwargs={'first_run': True},
        eta=spark_job.start_date,
    )


def test_first_run_with_run(mocker, spark_job):
    spark_job.runs.create()
    apply_async = mocker.patch('atmo.jobs.tasks.run_job.apply_async')
    spark_job.first_run()
    assert not apply_async.called


def test_first_run_should_run(one_hour_ago, spark_job):
    spark_job.start_date = one_hour_ago
    assert spark_job.has_never_run
    assert not spark_job.has_finished
    assert spark_job.is_runnable
    assert spark_job.should_run


def test_not_active_should_run(one_hour_ahead, spark_job):
    spark_job.start_date = one_hour_ahead
    assert not spark_job.should_run


def test_expired_should_run(mocker, now, one_hour_ago, spark_job):
    mocker.patch(
        'django.utils.timezone.now',
        return_value=now + timedelta(seconds=1)
    )
    spark_job.start_date = one_hour_ago
    spark_job.end_date = now
    assert not spark_job.should_run


def test_second_run_should_run(now, emr_release, spark_job):
    spark_job.interval_in_hours = 1
    spark_job.start_date = now - timedelta(days=1)
    spark_job.runs.create(
        scheduled_at=now - timedelta(hours=2),
        status=Cluster.STATUS_TERMINATED,
        emr_release_version=emr_release.version,
    )
    assert spark_job.should_run


@pytest.fixture
def has_timed_out_factory(now, spark_job):
    def factory():
        spark_job.start_date = now - timedelta(hours=48)  # started two days ago
        spark_job.job_timeout = 12  # hours after which the job should timeout
        spark_job.runs.create(jobflow_id='my-jobflow-id')
        timeout_delta = timedelta(hours=spark_job.job_timeout)
        return spark_job, timeout_delta
    return factory


def test_has_timed_out_never_ran(has_timed_out_factory):
    "No last scheduled_at and no status"
    spark_job, timeout_delta = has_timed_out_factory()
    spark_job.latest_run.scheduled_at = None
    spark_job.latest_run.status = models.DEFAULT_STATUS
    assert not spark_job.is_active
    assert spark_job.is_runnable
    assert spark_job.has_never_run
    assert not spark_job.has_timed_out


def test_has_timed_never_ran_faulty_state(has_timed_out_factory):
    "No last scheduled_at and running status"
    spark_job, timeout_delta = has_timed_out_factory()
    spark_job.latest_run.scheduled_at = None
    spark_job.latest_run.status = Cluster.STATUS_RUNNING
    assert spark_job.is_runnable
    assert spark_job.has_never_run
    assert not spark_job.has_timed_out


def test_has_timed_out_ran_and_terminated(has_timed_out_factory):
    "Most recent status != RUNNING"
    spark_job, timeout_delta = has_timed_out_factory()
    spark_job.latest_run.scheduled_at = spark_job.start_date + timedelta(minutes=10)
    spark_job.latest_run.status = Cluster.STATUS_TERMINATED
    assert not spark_job.is_active
    assert spark_job.is_runnable
    assert not spark_job.has_never_run
    assert not spark_job.has_timed_out


def test_has_timed_out_running_just_passed_timeout(now, has_timed_out_factory):
    "It hasn't run for more than its timeout"
    spark_job, timeout_delta = has_timed_out_factory()
    # now - 12h + 10mins
    spark_job.latest_run.scheduled_at = (
        now - timeout_delta + timedelta(minutes=10)
    )
    spark_job.latest_run.status = Cluster.STATUS_RUNNING
    assert not spark_job.is_runnable
    assert not spark_job.has_never_run
    assert not spark_job.has_timed_out


def test_has_timed_out_for_real(now, has_timed_out_factory):
    "All the conditions are met"
    spark_job, timeout_delta = has_timed_out_factory()
    # now - 12h - 10mins
    spark_job.latest_run.scheduled_at = (
        now - timeout_delta - timedelta(minutes=10)
    )
    spark_job.latest_run.status = Cluster.STATUS_RUNNING
    assert not spark_job.is_runnable
    assert not spark_job.has_never_run
    assert spark_job.has_timed_out


def test_terminates(now, spark_job, cluster_provisioner_mocks):
    # Test that a spark job's `terminate` tells the EMR to terminate correctly.
    spark_job.runs.create(jobflow_id='jobflow-id')

    timeout_date = now - timedelta(hours=12)
    running_status = Cluster.STATUS_RUNNING

    # Test job terminates
    spark_job.latest_run.scheduled_at = timeout_date
    spark_job.latest_run.status = running_status
    spark_job.terminate()
    cluster_provisioner_mocks['stop'].assert_called_with(u'jobflow-id')


def test_doesnt_terminate(now, spark_job):
    assert not spark_job.terminate()


def test_expires(mocker, now, spark_job_factory, cluster_provisioner_mocks):
    # create a spark job and a schedule entry
    spark_job = spark_job_factory(
        end_date=now - timedelta(hours=1)
    )
    spark_job.schedule.add()
    assert spark_job.schedule.get()
    # the expired date obviously wasn't set before
    assert not spark_job.expired_date
    # now expire it and see if the result is truthy
    result = spark_job.expire()
    assert result
    # then check if the expired_date was set
    spark_job.refresh_from_db()
    assert spark_job.expired_date

    # now reset the end_date to after now() and see if it
    # resets expired_date again to None
    spark_job.end_date = now + timedelta(days=1)
    spark_job.save()
    spark_job.refresh_from_db()
    assert not spark_job.expired_date
