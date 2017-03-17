# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta
from urllib.parse import urljoin

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

from atmo.clusters.provisioners import ClusterProvisioner

from ..clusters.models import Cluster
from ..models import (CreatedByModel, EditedAtModel, EMRReleaseModel,
                      ForgivingOneToOneField)
from .provisioners import SparkJobProvisioner

DEFAULT_STATUS = ''


class SparkJobQuerySet(models.QuerySet):

    def with_runs(self):
        return self.filter(runs__isnull=False)

    def active(self):
        return self.filter(
            runs__status__in=Cluster.ACTIVE_STATUS_LIST,
        )

    def terminated(self):
        return self.filter(
            most_recent_status__in=Cluster.TERMINATED_STATUS_LIST,
        )

    def failed(self):
        return self.filter(
            most_recent_status__in=Cluster.FAILED_STATUS_LIST,
        )


class SparkJob(EMRReleaseModel, CreatedByModel):
    INTERVAL_DAILY = 24
    INTERVAL_WEEKLY = INTERVAL_DAILY * 7
    INTERVAL_MONTHLY = INTERVAL_DAILY * 30
    INTERVAL_CHOICES = [
        (INTERVAL_DAILY, 'Daily'),
        (INTERVAL_WEEKLY, 'Weekly'),
        (INTERVAL_MONTHLY, 'Monthly'),
    ]
    RESULT_PRIVATE = 'private'
    RESULT_PUBLIC = 'public'
    RESULT_VISIBILITY_CHOICES = [
        (RESULT_PRIVATE, 'Private'),
        (RESULT_PUBLIC, 'Public'),
    ]

    identifier = models.CharField(
        max_length=100,
        help_text="Job name, used to uniqely identify individual jobs.",
        unique=True,
    )
    description = models.TextField(
        help_text='Job description.',
        default='',
    )
    notebook_s3_key = models.CharField(
        max_length=800,
        help_text="S3 key of the notebook after uploading it to the Spark code bucket."
    )
    result_visibility = models.CharField(  # can currently be "public" or "private"
        max_length=50,
        help_text="Whether notebook results are uploaded to a public or private bucket",
        choices=RESULT_VISIBILITY_CHOICES,
        default=RESULT_PRIVATE,
    )
    size = models.IntegerField(
        help_text="Number of computers to use to run the job."
    )
    interval_in_hours = models.IntegerField(
        help_text="Interval at which the job should run, in hours.",
        choices=INTERVAL_CHOICES,
        default=INTERVAL_DAILY,
    )
    job_timeout = models.IntegerField(
        help_text="Number of hours before the job times out.",
    )
    start_date = models.DateTimeField(
        help_text="Date/time that the job should start being scheduled to run."
    )
    end_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date/time that the job should stop being scheduled to run, null if no end date."
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Whether the job should run or not."
    )

    objects = SparkJobQuerySet.as_manager()

    class Meta:
        permissions = [
            ('view_sparkjob', 'Can view Spark job'),
        ]

    def __str__(self):
        return self.identifier

    def __repr__(self):
        return "<SparkJob {} with {} nodes>".format(self.identifier, self.size)

    @property
    def provisioner(self):
        return SparkJobProvisioner()

    # TEMPORARY till we have 1:1 relationship to cluster object
    # and we can then ask for spark_job.cluster.provisioner
    @property
    def cluster_provisioner(self):
        return ClusterProvisioner()

    @property
    def has_never_run(self):
        """
        Whether the job has run before.
        Looks at both the cluster status and our own record when
        we asked it to run.
        """
        return (self.latest_run is None or
                self.latest_run.status == DEFAULT_STATUS or
                self.latest_run.scheduled_date is None)

    @property
    def has_finished(self):
        """Whether the job's cluster is terminated or failed"""
        return (self.latest_run and
                self.latest_run.status in Cluster.FINAL_STATUS_LIST)

    @property
    def is_runnable(self):
        """
        Either the job has never run before or was never finished
        """
        return self.has_never_run or self.has_finished

    @property
    def is_expired(self):
        """Whether the current job run has run out of time"""
        if self.has_never_run:
            # Job isn't even running at the moment and never ran before
            return False
        max_run_time = (self.latest_run.scheduled_date +
                        timedelta(hours=self.job_timeout))
        return not self.is_runnable and timezone.now() >= max_run_time

    @property
    def is_public(self):
        return self.result_visibility == self.RESULT_PUBLIC

    @property
    def notebook_name(self):
        return self.notebook_s3_key.rsplit('/', 1)[-1]

    def get_latest_run(self):
        try:
            return self.runs.latest()
        except SparkJobRun.DoesNotExist:
            return None
    latest_run = cached_property(get_latest_run, name='latest_run')

    @cached_property
    def notebook_s3_object(self):
        return self.provisioner.get(self.notebook_s3_key)

    def get_absolute_url(self):
        return reverse('jobs-detail', kwargs={'id': self.id})

    def get_full_url(self):
        return urljoin(settings.SITE_URL, self.get_absolute_url())

    def is_due(self, now=None):
        """
        Whether the scheduled Spark job is due to be run based on the
        latest run and the configured interval in hours.
        """
        if now is None:
            now = timezone.now()
        if not self.latest_run or self.latest_run.scheduled_date is None:
            # job has never run before
            hours_since_last_run = float('inf')
        else:
            hours_since_last_run = (now - self.latest_run.scheduled_date).total_seconds() // 3600

        return hours_since_last_run >= self.interval_in_hours

    def should_run(self):
        """Whether the scheduled Spark job should run."""
        if not self.is_runnable:
            return False  # the job is still running, don't start it again
        now = timezone.now()
        active = self.start_date <= now
        if self.end_date is not None:
            active = active and self.end_date >= now
        return (
            self.is_enabled and
            active and
            self.is_due(now)
        )

    def run(self):
        """Actually run the scheduled Spark job."""
        # if the job ran before and is still running, don't start it again
        if not self.is_runnable:
            return
        jobflow_id = self.provisioner.run(
            user_email=self.created_by.email,
            identifier=self.identifier,
            emr_release=self.emr_release,
            size=self.size,
            notebook_key=self.notebook_s3_key,
            is_public=self.is_public,
            job_timeout=self.job_timeout,
        )
        # Create new job history record.
        run = self.runs.create(
            spark_job=self,
            jobflow_id=jobflow_id,
            scheduled_date=timezone.now(),
        )
        # Remove the cached latest run to this objects will requery it.
        try:
            delattr(self, 'latest_run')
        except AttributeError:
            pass  # It didn't have a `latest_run` and that's ok.
        run.update_status()

    def terminate(self):
        """Stop the currently running scheduled Spark job."""
        if self.is_expired and self.latest_run:
            self.cluster_provisioner.stop(self.latest_run.jobflow_id)

    def cleanup(self):
        """Remove the Spark job notebook file from S3"""
        self.provisioner.remove(self.notebook_s3_key)

    def delete(self, *args, **kwargs):
        # make sure to shut down the cluster if it's currently running
        self.terminate()
        # make sure to clean up the job notebook from storage
        self.cleanup()
        super().delete(*args, **kwargs)

    def get_results(self):
        return self.provisioner.results(self.identifier, self.is_public)


class SparkJobRun(EditedAtModel):

    spark_job = models.ForeignKey(
        SparkJob,
        on_delete=models.CASCADE,
        related_name='runs',
        related_query_name='runs',
    )
    jobflow_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=50,
        blank=True,
        default=DEFAULT_STATUS,
    )
    scheduled_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date/time that the job was scheduled.",
    )
    run_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date/time that the job was run.",
    )
    terminated_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date/time that the job was terminated.",
    )

    class Meta:
        get_latest_by = 'created_at'

    def __str__(self):
        return self.jobflow_id

    def __repr__(self):
        return "<SparkJobRun {} from job {}>".format(self.jobflow_id,
                                                     self.spark_job.identifier)

    def get_info(self):
        return self.spark_job.cluster_provisioner.info(self.jobflow_id)

    def update_status(self, info=None):
        """
        Updates latest status and life cycle datetimes.
        """
        if info is None:
            info = self.get_info()
        if self.status != info['state']:
            self.status = info['state']
            if self.status == Cluster.STATUS_RUNNING:
                self.run_date = timezone.now()
            elif self.status in Cluster.FINAL_STATUS_LIST:
                # set the terminated date to now
                self.terminated_date = timezone.now()
                # if the job cluster terminated with error raise the alarm
                if self.status == Cluster.STATUS_TERMINATED_WITH_ERRORS:
                    SparkJobRunAlert.objects.create(
                        run=self,
                        reason_code=info['state_change_reason_code'],
                        reason_message=info['state_change_reason_message'],
                    )
            self.save()
        return self.status


class SparkJobRunAlert(EditedAtModel):
    """
    A data model to store job run alerts for later processing by an
    async job that sends out emails.
    """
    run = ForgivingOneToOneField(
        SparkJobRun,
        on_delete=models.CASCADE,
        related_name='alert',  # run.alert & alert.run
        primary_key=True,
    )
    reason_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="The reason code for the creation of the alert.",
    )
    reason_message = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="The reason message for the creation of the alert.",
    )
    mail_sent_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="The datetime the alert email was sent.",
    )
