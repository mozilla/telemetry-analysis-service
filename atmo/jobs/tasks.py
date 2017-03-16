# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import logging

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from atmo.celery import celery
from atmo.clusters.models import Cluster
from atmo.clusters.provisioners import ClusterProvisioner

from .. import email
from .models import SparkJob, SparkJobRunAlert

logger = logging.getLogger(__name__)


@celery.autoretry_task()
def run_jobs():
    """
    Run all the scheduled tasks that are supposed to run.
    """
    # first let's update the job statuses if there are prior runs
    run_jobs = []
    jobs = SparkJob.objects.all()

    # get the jobs with prior runs
    jobs_with_active_runs = jobs.active().prefetch_related('runs')
    logger.debug('Updating Spark jobs: %s', jobs_with_active_runs)

    # create a map between the jobflow ids of the latest runs and the jobs
    jobflow_job_map = {
        job.latest_run.jobflow_id: job
        for job in jobs_with_active_runs
    }
    # get the created dates of the job runs to limit the ListCluster API call
    provisioner = ClusterProvisioner()
    runs_created_at = jobs_with_active_runs.datetimes('runs__created_at', 'day')

    # only fetch a cluster list if there are any runs at all
    if runs_created_at:
        logger.debug('Fetching clusters older than %s', runs_created_at[0])

        cluster_list = provisioner.list(created_after=runs_created_at[0])
        logger.debug('Clusters found: %s', cluster_list)

        for cluster_info in cluster_list:
            # filter out the clusters that don't relate to the job run ids
            job = jobflow_job_map.get(cluster_info['jobflow_id'], None)
            if job is None:
                continue
            logger.debug('Updating job status for %s, latest run %s', job, job.latest_run)
            # update the latest run status
            with transaction.atomic():
                job.latest_run.update_status(cluster_info)

    for job in jobs:
        with transaction.atomic():
            # then let's check if the job should be run at all
            should_run = job.should_run()
            logger.debug('Checking if job %s should run: %s', job, should_run)
            if should_run:
                job.run()
                run_jobs.append(job.identifier)

            # and then check if the job is expired and terminate it if needed
            if job.is_expired:
                logger.debug('Job %s is expired and is terminated', job)
                # This shouldn't be required as we set a timeout in the bootstrap script,
                # but let's keep it as a guard.
                job.terminate()
    return run_jobs


@celery.task
def send_run_alert_mails():
    failed_run_alerts = SparkJobRunAlert.objects.filter(
        reason_code__in=Cluster.FAILED_STATE_CHANGE_REASON_LIST,
        mail_sent_date__isnull=True,
    ).prefetch_related('run__spark_job__created_by')
    failed_jobs = []
    for alert in failed_run_alerts:
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
