# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from botocore.exceptions import ClientError
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from atmo.celery import celery
from atmo.clusters.models import Cluster
from atmo.clusters.provisioners import ClusterProvisioner

from .. import email
from .exceptions import SparkJobNotFound, SparkJobNotEnabled
from .models import SparkJob, SparkJobRunAlert

logger = get_task_logger(__name__)


@celery.task
def send_expired_mails():
    expired_spark_jobs = SparkJob.objects.filter(
        expired_date__isnull=False,
    )
    for spark_job in expired_spark_jobs:
        with transaction.atomic():
            subject = '[ATMO] Spark job %s expired' % spark_job.identifier
            body = render_to_string(
                'atmo/jobs/mails/expired_body.txt', {
                    'site_url': settings.SITE_URL,
                    'spark_job': spark_job,
                }
            )
            email.send_email(
                to=spark_job.created_by.email,
                cc=settings.AWS_CONFIG['EMAIL_SOURCE'],
                subject=subject,
                body=body
            )


@celery.task
def expire_jobs():
    """
    Periodic task to purge all schedule entries
    that don't have a SparkJob instance anymore
    """
    expired_spark_jobs = []
    for spark_job in SparkJob.objects.filter(end_date__lte=timezone.now()):
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


@celery.task(max_retries=3)
@celery.autoretry(ClientError)
def update_jobs_statuses():
    spark_jobs = SparkJob.objects.all()

    # get the jobs with prior runs
    spark_jobs_with_active_runs = spark_jobs.active().prefetch_related('runs')
    logger.debug(
        'Updating Spark jobs: %s',
        list(spark_jobs_with_active_runs.values_list('pk', flat=True))
    )

    # create a map between the jobflow ids of the latest runs and the jobs
    jobflow_spark_job_map = {
        spark_job.latest_run.jobflow_id:
        spark_job for spark_job in spark_jobs_with_active_runs
    }
    # get the created dates of the job runs to limit the ListCluster API call
    provisioner = ClusterProvisioner()
    runs_created_at = spark_jobs_with_active_runs.datetimes(
        'runs__created_at', 'day'
    )

    # only fetch a cluster list if there are any runs at all
    updated_spark_job_runs = []
    if runs_created_at:
        logger.debug('Fetching clusters older than %s', runs_created_at[0])

        cluster_list = provisioner.list(created_after=runs_created_at[0])
        logger.debug('Clusters found: %s', cluster_list)

        for cluster_info in cluster_list:
            # filter out the clusters that don't relate to the job run ids
            spark_job = jobflow_spark_job_map.get(
                cluster_info['jobflow_id'],
                None
            )
            if spark_job is None:
                continue
            logger.debug(
                'Updating job status for %s, latest run %s',
                spark_job,
                spark_job.latest_run,
            )
            # update the latest run status
            with transaction.atomic():
                spark_job.latest_run.update_status(cluster_info)
                updated_spark_job_runs.append(
                    [spark_job.identifier, spark_job.pk]
                )
    return updated_spark_job_runs


class SparkJobRunTask(celery.Task):
    throws = (
        SparkJobNotFound,
        SparkJobNotEnabled,
    )
    max_retries = 3

    @transaction.atomic
    def update_status(self, spark_job):
        """
        Updates the cluster status of the latest Spark job run,
        if available.
        """
        if spark_job.latest_run:
            logger.debug('Updating Spark job: %s', spark_job)
            spark_job.latest_run.update_status()
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
    def provision_run(self, spark_job):
        spark_job.run()

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

    def terminate_and_retry(self, spark_job):
        logger.debug(
            'The last run of Spark job %s has not finished yet and timed out, '
            'terminating it', spark_job,
        )
        spark_job.terminate()
        self.retry(countdown=60 * 5)


@celery.task(bind=True, base=SparkJobRunTask)
@celery.autoretry(ClientError)
def run_job(self, pk):
    """
    Run the Spark job with the given primary key.
    """
    spark_job = SparkJob.objects.filter(pk=pk).first()
    if spark_job is None:
        raise SparkJobNotFound('Cannot find Spark job with pk %s' % pk)

    # update the cluster status of the latest Spark job run
    updated = self.update_status(spark_job)
    if updated:
        spark_job.refresh_from_db()

    self.check_enabled(spark_job)

    if spark_job.has_finished():
        # if the latest run of the Spark job has finished
        if spark_job.is_due():
            # if current datetime is between Spark job's start and end date
            self.provision_run(spark_job)
        else:
            # otherwise remove the job from the schedule and send
            # an email to the Spark job owner
            self.unschedule_and_expire(spark_job)
    else:
        if spark_job.has_timed_out():
            # if the job has not finished and timed out
            self.terminate_and_retry(spark_job)
        else:
            # if the job hasn't finished yet but also hasn't timed out
            # since the job timeout is limited to 24 hours
            # this case can only happen for daily jobs that have a scheduling
            # or processing delay. we just retry again in a few minutes
            # and see if we caught up with the delay
            self.retry(countdown=60 * 10)


@celery.task
def send_run_alert_mails():
    failed_run_alerts = SparkJobRunAlert.objects.filter(
        reason_code__in=Cluster.FAILED_STATE_CHANGE_REASON_LIST,
        mail_sent_date__isnull=True,
    ).prefetch_related('run__spark_job__created_by')
    failed_jobs = []
    for alert in failed_run_alerts:
        with transaction.atomic():
            failed_jobs.append(alert.run.spark_job.identifier)
            subject = '[ATMO] Running Spark job %s failed' % alert.run.spark_job.identifier
            body = render_to_string(
                'atmo/jobs/mails/failed_run_alert_body.txt', {
                    'alert': alert,
                    'site_url': settings.SITE_URL,
                }
            )
            email.send_email(
                to=alert.run.spark_job.created_by.email,
                cc=settings.AWS_CONFIG['EMAIL_SOURCE'],
                subject=subject,
                body=body
            )
            alert.mail_sent_date = timezone.now()
            alert.save()
    return failed_jobs
