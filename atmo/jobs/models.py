# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

import urlman
from autorepr import autorepr, autostr
from django.core.urlresolvers import reverse
from django.db import models, transaction
from django.utils import timezone
from django.utils.functional import cached_property

from ..clusters.models import Cluster, EMRReleaseModel
from ..clusters.provisioners import ClusterProvisioner
from ..models import CreatedByModel, EditedAtModel, ForgivingOneToOneField

from .provisioners import SparkJobProvisioner

DEFAULT_STATUS = ''


class SparkJobQuerySet(models.QuerySet):

    def with_runs(self):
        """
        The Spark jobs with runs.
        """
        return self.filter(runs__isnull=False)

    def active(self):
        """
        The Spark jobs that have an active cluster status.
        """
        return self.filter(
            runs__status__in=Cluster.ACTIVE_STATUS_LIST,
        )

    def terminated(self):
        """
        The Spark jobs that have a terminated cluster status.
        """
        return self.filter(
            runs__status__in=Cluster.TERMINATED_STATUS_LIST,
        )

    def failed(self):
        """
        The Spark jobs that have a failed cluster status.
        """
        return self.filter(
            runs__status__in=Cluster.FAILED_STATUS_LIST,
        )

    def lapsed(self):
        """
        The Spark jobs that have passed their end dates
        but haven't been expired yet.
        """
        return self.filter(
            end_date__lte=timezone.now(),
            expired_date__isnull=True,
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
    expired_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date/time that the job was expired."
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

    class urls(urlman.Urls):

        def delete(self):
            return reverse('jobs-delete', kwargs={'id': self.id})

        def detail(self):
            return reverse('jobs-detail', kwargs={'id': self.id})

        def download(self):
            return reverse('jobs-download', kwargs={'id': self.id})

        def edit(self):
            return reverse('jobs-edit', kwargs={'id': self.id})

    __str__ = autostr('{self.identifier}')

    __repr__ = autorepr(['identifier', 'size', 'is_enabled'])

    def get_absolute_url(self):
        return self.urls.detail

    @property
    def provisioner(self):
        return SparkJobProvisioner()

    # TEMPORARY till we have 1:1 relationship to cluster object
    # and we can then ask for spark_job.cluster.provisioner
    @property
    def cluster_provisioner(self):
        return ClusterProvisioner()

    @property
    def schedule(self):
        from .schedules import SparkJobSchedule
        return SparkJobSchedule(self)

    @property
    def results(self):
        return self.provisioner.results(self.identifier, self.is_public)

    def has_future_end_date(self, now):
        # no end date means it'll always be due
        if self.end_date is None:
            return True
        return self.end_date >= now

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
    def has_timed_out(self):
        """
        Whether the current job run has been running longer than the
        job's timeout allows.
        """
        if self.has_never_run:
            # Job isn't even running at the moment and never ran before
            return False
        timeout_delta = timedelta(hours=self.job_timeout)
        max_run_time = self.latest_run.scheduled_date + timeout_delta
        timed_out = timezone.now() >= max_run_time
        return not self.is_runnable and timed_out

    @property
    def is_due(self):
        """
        Whether the start date is in the past and the end date is in the
        future.
        """
        now = timezone.now()
        has_past_start_date = self.start_date <= now
        return has_past_start_date and self.has_future_end_date(now)

    @property
    def is_runnable(self):
        """
        Either the job has never run before or was never finished.

        This is checked right before the actual provisioning.
        """
        return self.has_never_run or self.has_finished

    @property
    def should_run(self):
        """Whether the scheduled Spark job should run."""
        return self.is_runnable and self.is_enabled and self.is_due

    @property
    def is_public(self):
        return self.result_visibility == self.RESULT_PUBLIC

    @property
    def notebook_name(self):
        return self.notebook_s3_key.rsplit('/', 1)[-1]

    @cached_property
    def notebook_s3_object(self):
        return self.provisioner.get(self.notebook_s3_key)

    def get_latest_run(self):
        try:
            return self.runs.latest()
        except SparkJobRun.DoesNotExist:
            return None
    latest_run = cached_property(get_latest_run, name='latest_run')

    def run(self):
        """Actually run the scheduled Spark job."""
        # if the job ran before and is still running, don't start it again
        if not self.is_runnable:
            return
        jobflow_id = self.provisioner.run(
            user_email=self.created_by.email,
            identifier=self.identifier,
            emr_release=self.emr_release.version,
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
            emr_release_version=self.emr_release.version,
        )
        # Remove the cached latest run to this objects will requery it.
        try:
            delattr(self, 'latest_run')
        except AttributeError:  # pragma: no cover
            pass  # It didn't have a `latest_run` and that's ok.
        run.update_status()

    def expire(self):
        # TODO disable the job as well once it's easy to re-enable the job
        deleted = self.schedule.delete()
        self.expired_date = timezone.now()
        self.save()
        return deleted

    def terminate(self):
        """Stop the currently running scheduled Spark job."""
        if self.latest_run:
            self.cluster_provisioner.stop(self.latest_run.jobflow_id)

    def first_run(self):
        if self.latest_run:
            return None
        from .tasks import run_job
        return run_job.apply_async(
            args=(self.pk,),
            # make sure we run this task only when we expect it
            # may be in the future, may be in the past
            # but definitely at a specific time
            eta=self.start_date,
        )

    def save(self, *args, **kwargs):
        # whether the job is being created for the first time
        first_save = self.pk is None
        # resetting expired_date in case a user resets the end_date
        if self.expired_date and self.end_date and self.end_date > timezone.now():
            self.expired_date = None
        super().save(*args, **kwargs)
        # first remove if it exists
        self.schedule.delete()
        # and then add it, but only if the end date is in the future
        if self.has_future_end_date(timezone.now()):
            self.schedule.add()
        if first_save:
            transaction.on_commit(self.first_run)

    def delete(self, *args, **kwargs):
        # make sure to shut down the cluster if it's currently running
        self.terminate()
        # make sure to clean up the job notebook from storage
        self.provisioner.remove(self.notebook_s3_key)
        self.schedule.delete()
        super().delete(*args, **kwargs)


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
    emr_release_version = models.CharField(
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

    __str__ = autostr('{self.jobflow_id}')

    def spark_job_identifier(self):
        return self.spark_job.identifier

    __repr__ = autorepr(
        ['jobflow_id', 'spark_job_identifier'],
        spark_job_identifier=spark_job_identifier,
    )

    @property
    def info(self):
        return self.spark_job.cluster_provisioner.info(self.jobflow_id)

    def update_status(self, info=None):
        """
        Updates latest status and life cycle datetimes.
        """
        if info is None:
            info = self.info
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
    reason_message = models.TextField(
        default='',
        help_text="The reason message for the creation of the alert.",
    )
    mail_sent_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="The datetime the alert email was sent.",
    )
