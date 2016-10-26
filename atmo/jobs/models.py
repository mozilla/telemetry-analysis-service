# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

from django.core.urlresolvers import reverse
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.functional import cached_property

from ..models import EMRReleaseModel
from .. import provisioning, scheduling
from ..clusters.models import Cluster


class SparkJob(EMRReleaseModel):
    DAILY = 24
    WEEKLY = DAILY * 7
    MONTHLY = DAILY * 30
    INTERVAL_CHOICES = [
        (DAILY, "Daily"),
        (WEEKLY, "Weekly"),
        (MONTHLY, "Monthly"),
    ]
    INTERVAL_CHOICES_DEFAULT = INTERVAL_CHOICES[0][0]
    RESULT_VISIBILITY_CHOICES = [
        ('private', 'Private: results output to an S3 bucket, viewable with AWS credentials'),
        ('public', 'Public: results output to a public S3 bucket, viewable by anyone'),
    ]
    RESULT_VISIBILITY_CHOICES_DEFAULT = RESULT_VISIBILITY_CHOICES[0][0]

    identifier = models.CharField(
        max_length=100,
        help_text="Job name, used to uniqely identify individual jobs.",
        unique=True,
    )
    notebook_s3_key = models.CharField(
        max_length=800,
        help_text="S3 key of the notebook after uploading it to the Spark code bucket."
    )
    result_visibility = models.CharField(  # can currently be "public" or "private"
        max_length=50,
        help_text="Whether notebook results are uploaded to a public or private bucket",
        choices=RESULT_VISIBILITY_CHOICES,
        default=RESULT_VISIBILITY_CHOICES_DEFAULT,
    )
    size = models.IntegerField(
        help_text="Number of computers to use to run the job."
    )
    interval_in_hours = models.IntegerField(
        help_text="Interval at which the job should run, in hours.",
        choices=INTERVAL_CHOICES,
        default=INTERVAL_CHOICES_DEFAULT,
    )
    job_timeout = models.IntegerField(
        help_text="Number of hours before the job times out.",
    )
    start_date = models.DateTimeField(
        help_text="Date/time that the job should start being scheduled to run."
    )
    end_date = models.DateTimeField(
        blank=True, null=True,
        help_text="Date/time that the job should stop being scheduled to run, null if no end date."
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Whether the job should run or not."
    )
    last_run_date = models.DateTimeField(
        blank=True, null=True,
        help_text="Date/time that the job was last started, null if never."
    )
    created_by = models.ForeignKey(
        User,
        related_name='created_spark_jobs',
        help_text="User that created the scheduled job instance."
    )

    current_run_jobflow_id = models.CharField(max_length=50, blank=True, null=True)
    most_recent_status = models.CharField(max_length=50, default="NOT RUNNING")

    def __str__(self):
        return self.identifier

    def __repr__(self):
        return "<SparkJob {} with {} nodes>".format(self.identifier, self.size)

    def get_info(self):
        if self.current_run_jobflow_id is None:
            return None
        return provisioning.cluster_info(self.current_run_jobflow_id)

    def update_status(self):
        """Should be called to update latest cluster status in `self.most_recent_status`."""
        info = self.get_info()
        if info is None:
            self.most_recent_status = "NOT RUNNING"
        else:
            self.most_recent_status = info["state"]
        return self.most_recent_status

    def is_expired(self, at_time=None):
        """Tells whether the current job run has run out of time or not"""
        if not self.current_run_jobflow_id or not self.last_run_date:
            # Job isn't even running at the moment and never ran before
            return False
        if at_time is None:
            at_time = timezone.now()
        max_run_time = self.last_run_date + timedelta(hours=self.job_timeout)
        return self.most_recent_status not in Cluster.FINAL_STATUS_LIST and at_time >= max_run_time

    def should_run(self, at_time=None):
        """Return True if the scheduled Spark job should run, False otherwise."""
        if self.current_run_jobflow_id is not None:
            return False  # the job is still running, don't start it again
        if at_time is None:
            at_time = timezone.now()
        active = self.start_date <= at_time
        if self.end_date is not None:
            active = active and self.end_date >= at_time
        hours_since_last_run = (
            float("inf")  # job was never run before
            if self.last_run_date is None else
            (at_time - self.last_run_date).total_seconds() / 3600
        )
        can_run_now = hours_since_last_run >= self.interval_in_hours
        return self.is_enabled and active and can_run_now

    def run(self):
        """Actually run the scheduled Spark job."""
        if self.current_run_jobflow_id is not None:
            return  # the job is still running, don't start it again
        self.current_run_jobflow_id = scheduling.spark_job_run(
            self.created_by.email,
            self.identifier,
            self.notebook_s3_key,
            self.is_public,
            self.size,
            self.job_timeout,
            self.emr_release,
        )
        self.last_run_date = timezone.now()
        self.update_status()
        self.save()

    @property
    def is_public(self):
        return self.result_visibility == 'public'

    @property
    def notebook_name(self):
        return self.notebook_s3_key.rsplit('/', 1)[-1]

    @cached_property
    def notebook_content(self):
        if self.notebook_s3_key:
            return scheduling.spark_job_get(self.notebook_s3_key)

    def terminate(self):
        """Stop the currently running scheduled Spark job."""
        if self.current_run_jobflow_id:
            provisioning.cluster_stop(self.current_run_jobflow_id)

    def cleanup(self):
        """Remove the Spark job notebook file from S3"""
        if self.notebook_s3_key:
            scheduling.spark_job_remove(self.notebook_s3_key)

    def save(self, notebook_uploadedfile=None, *args, **kwargs):
        if notebook_uploadedfile is not None:  # notebook specified, replace current notebook
            self.notebook_s3_key = scheduling.spark_job_add(
                self.identifier,
                notebook_uploadedfile
            )
        return super(SparkJob, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # make sure to shut down the cluster if it's currently running
        self.terminate()
        # make sure to clean up the job notebook from storage
        self.cleanup()
        super(SparkJob, self).delete(*args, **kwargs)

    @classmethod
    def step_all(cls):
        """Run all the scheduled tasks that are supposed to run."""
        for spark_jobs in cls.objects.all():
            if spark_jobs.should_run():
                spark_jobs.run()
            if spark_jobs.is_expired():
                # This shouldn't be required as we set a timeout in the bootstrap script,
                # but let's keep it as a guard.
                spark_jobs.terminate()

    def get_absolute_url(self):
        return reverse('jobs-detail', kwargs={'id': self.id})
