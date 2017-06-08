# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import mail_builder
from botocore.exceptions import ClientError
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from atmo.celery import celery
from atmo.clusters.models import Cluster
from atmo.clusters.provisioners import ClusterProvisioner

from .exceptions import SparkJobNotFound, SparkJobNotEnabled
from .models import SparkJob, SparkJobRun, SparkJobRunAlert

logger = get_task_logger(__name__)


@celery.task
def send_expired_mails():
    """
    A Celery task the send emails for when a Spark job as expired
    (the end_date has passed) to the owner.
    """
    expired_spark_jobs = SparkJob.objects.filter(
        expired_date__isnull=False,
    )
    for spark_job in expired_spark_jobs:
        message = mail_builder.build_message(
            'atmo/jobs/mails/expired.mail', {
                'settings': settings,
                'spark_job': spark_job,
            }
        )
        message.send()


@celery.task
def expire_jobs():
    """
    Periodic task to purge all schedule entries
    that don't have a SparkJob instance anymore
    """
    expired_spark_jobs = []
    for spark_job in SparkJob.objects.lapsed():
        with transaction.atomic():
            expired_spark_jobs.append([spark_job.identifier, spark_job.pk])
            removed = spark_job.expire()
            logger.info(
                'Spark job %s (%s) is expired.',
                spark_job.pk,
                spark_job.identifier,
            )
            if removed:
                logger.info(
                    'Removing expired Spark job %s (%s) from schedule.',
                    spark_job.pk,
                    spark_job.identifier,
                )

    return expired_spark_jobs


@celery.task(max_retries=8, bind=True)
def update_jobs_statuses(self):
    """
    A Celery task that updates the status of all active
    job runs using the AWS EMR API or retry with an exponential backoff
    when a certain number of failures have happened.

    This task runs every 15 minutes (900 seconds, see ``CELERY_BEAT_SCHEDULE``
    setting), which fits nicely in the backoff decay of 9 tries total
    """
    spark_job_runs = SparkJobRun.objects.all()

    # get the active (read: not terminated or failed) job runs
    active_spark_job_runs = spark_job_runs.active().prefetch_related('spark_job')
    logger.debug(
        'Updating Spark job runs: %s',
        list(active_spark_job_runs.values_list('pk', flat=True))
    )

    # create a map between the jobflow ids of the latest runs and the jobs
    spark_job_run_map = {}
    for spark_job_run in active_spark_job_runs:
        spark_job_run_map[spark_job_run.jobflow_id] = spark_job_run

    # get the created dates of the job runs to limit the ListCluster API call
    provisioner = ClusterProvisioner()
    runs_created_at = active_spark_job_runs.datetimes('created_at', 'day')

    try:
        # only fetch a cluster list if there are any runs at all
        updated_spark_job_runs = []
        if runs_created_at:
            earliest_created_at = runs_created_at[0]
            logger.debug('Fetching clusters since %s', earliest_created_at)

            cluster_list = provisioner.list(created_after=earliest_created_at)
            logger.debug('Clusters found: %s', cluster_list)

            for cluster_info in cluster_list:
                # filter out the clusters that don't relate to the job run ids
                spark_job_run = spark_job_run_map.get(cluster_info['jobflow_id'])
                if spark_job_run is None:
                    continue
                logger.debug(
                    'Updating job status for %s, run %s',
                    spark_job_run.spark_job,
                    spark_job_run,
                )
                # update the Spark job run status
                with transaction.atomic():
                    spark_job_run.sync(cluster_info)
                    updated_spark_job_runs.append(
                        [spark_job_run.spark_job.identifier, spark_job_run.pk]
                    )
        return updated_spark_job_runs
    except ClientError as exc:
        self.retry(
            exc=exc,
            countdown=celery.backoff(self.request.retries),
        )


class SparkJobRunTask(celery.Task):
    """
    A Celery task base classes to be used by the
    :func:`~atmo.jobs.tasks.run_job` task to simplify testing.
    """
    throws = (
        SparkJobNotFound,
        SparkJobNotEnabled,
    )
    #: The max number of retries which does not run too long
    #: when using the exponential backoff timeouts.
    max_retries = 9

    def get_spark_job(self, pk):
        """
        Load the Spark job with the given primary key.
        """
        spark_job = SparkJob.objects.filter(pk=pk).first()
        if spark_job is None:
            raise SparkJobNotFound('Cannot find Spark job with pk %s' % pk)
        return spark_job

    @transaction.atomic
    def sync_run(self, spark_job):
        """
        Updates the cluster status of the latest Spark job run,
        if available.
        """
        if spark_job.latest_run:
            logger.debug('Updating Spark job: %s', spark_job)
            spark_job.latest_run.sync()
            return True

    def check_enabled(self, spark_job):
        """
        Checks if the job should be run at all
        """
        if not spark_job.is_enabled:
            # just ignore this
            raise SparkJobNotEnabled(
                'Spark job %s is not enabled, ignoring' %
                spark_job
            )

    @transaction.atomic
    def provision_run(self, spark_job, first_run=False):
        """
        Actually run the given Spark job.

        If this is the first run we'll update the "last_run_at" value
        to the start date of the spark_job so Celery beat knows what's
        going on.
        """
        spark_job.run()
        if first_run:
            def update_last_run_at():
                schedule_entry = spark_job.schedule.get()
                if schedule_entry is None:
                    schedule_entry = spark_job.schedule.add()
                schedule_entry.reschedule(last_run_at=spark_job.start_date)
            transaction.on_commit(update_last_run_at)

    @transaction.atomic
    def unschedule_and_expire(self, spark_job):
        """
        Remove the Spark job from the periodic schedule
        and send an email to the owner that it was expired.
        """
        logger.debug(
            'The Spark job %s has expired was removed from the schedule',
            spark_job,
        )
        spark_job.schedule.delete()
        spark_job.expire()

    def terminate_and_notify(self, spark_job):
        """
        When the Spark job has timed out because it has run longer
        than the maximum runtime we will terminate it (and its cluster)
        and notify the owner to optimize the Spark job code.
        """
        logger.debug(
            'The last run of Spark job %s has not finished yet and timed out, '
            'terminating it and notifying owner.', spark_job,
        )
        spark_job.terminate()
        message = mail_builder.build_message(
            'atmo/jobs/mails/timed_out.mail', {
                'settings': settings,
                'spark_job': spark_job,
            }
        )
        message.send()


@celery.task(bind=True, base=SparkJobRunTask)
def run_job(self, pk, first_run=False):
    """
    Run the Spark job with the given primary key.

    See :class:`~atmo.jobs.tasks.SparkJobRunTask` for more details.
    """
    try:
        # get the Spark job (may fail with exception)
        spark_job = self.get_spark_job(pk)

        # update the cluster status of the latest Spark job run
        updated = self.sync_run(spark_job)
        if updated:
            spark_job.refresh_from_db()

        # check if the Spark job is enabled (may fail with exception)
        self.check_enabled(spark_job)

        if spark_job.is_runnable:
            # if the latest run of the Spark job has finished
            if spark_job.is_due:
                # if current datetime is between Spark job's start and end date
                self.provision_run(spark_job, first_run=first_run)
            else:
                # otherwise remove the job from the schedule and send
                # an email to the Spark job owner
                self.unschedule_and_expire(spark_job)
        else:
            if spark_job.has_timed_out:
                # if the job has not finished and timed out
                self.terminate_and_notify(spark_job)
            else:
                # if the job hasn't finished yet and also hasn't timed out yet.
                # since the job timeout is limited to 24 hours this case can
                # only happen for daily jobs that have a scheduling or processing
                # delay, e.g. slow provisioning. we just retry again in a few
                # minutes and see if we caught up with the delay
                self.retry(countdown=60 * 10)

    except ClientError as exc:
        self.retry(
            exc=exc,
            countdown=celery.backoff(self.request.retries),
        )


@celery.task
def send_run_alert_mails():
    """
    A Celery task that sends an email to the owner when a Spark job run has
    failed and records a datetime when it was sent.
    """
    with transaction.atomic():
        failed_run_alerts = SparkJobRunAlert.objects.select_for_update().filter(
            reason_code__in=Cluster.FAILED_STATE_CHANGE_REASON_LIST,
            mail_sent_date__isnull=True,
        ).prefetch_related('run__spark_job__created_by')
        failed_jobs = []
        for alert in failed_run_alerts:
            with transaction.atomic():
                failed_jobs.append(alert.run.spark_job.identifier)
                message = mail_builder.build_message(
                    'atmo/jobs/mails/failed_run_alert.mail', {
                        'alert': alert,
                        'settings': settings,
                    }
                )
                message.send()
                alert.mail_sent_date = timezone.now()
                alert.save()
    return failed_jobs
