from datetime import datetime, timedelta
from pytz import UTC
from django.db import models
from django.contrib.auth.models import User

from analysis_service.base.util import provisioning, scheduling


class Cluster(models.Model):
    identifier = models.CharField(
        max_length=100,
        help_text="Cluster name, used to non-uniqely identify individual clusters."
    )
    size = models.IntegerField(
        help_text="Number of computers  used in the cluster."
    )
    public_key = models.CharField(
        max_length=100000,
        help_text="Public key that should be authorized for SSH access to the cluster."
    )
    start_date = models.DateTimeField(
        blank=True, null=True,
        help_text="Date/time that the cluster was started, or null if it isn't started yet."
    )
    end_date = models.DateTimeField(
        blank=True, null=True,
        help_text="Date/time that the cluster will expire and automatically be killed."
    )
    created_by = models.ForeignKey(
        User, related_name='cluster_created_by',
        help_text="User that created the cluster instance."
    )

    jobflow_id = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="AWS cluster/jobflow ID for the cluster, used for cluster management."
    )
    most_recent_status = models.CharField(
        max_length=50, default="UNKNOWN",
        help_text="Most recently retrieved AWS status for the cluster."
    )

    def __str__(self):
        return self.identifier

    def __repr__(self):
        return "<Cluster {} of size {}>".format(self.identifier, self.size)

    def get_info(self):
        return provisioning.cluster_info(self.jobflow_id)

    def is_expiring_soon(self):
        """Returns true if the cluster is expiring in the next hour."""
        return self.end_date <= datetime.now().replace(tzinfo=UTC) + timedelta(hours=1)

    def update_status(self):
        """Should be called to update latest cluster status in `self.most_recent_status`."""
        info = self.get_info()
        self.most_recent_status = info["state"]
        return self.most_recent_status

    def update_identifier(self):
        """Should be called after changing the cluster's identifier, to update the name on AWS."""
        provisioning.cluster_rename(self.jobflow_id, self.identifier)
        return self.identifier

    def save(self, *args, **kwargs):
        """
        Insert the cluster into the database or update it if already present,
        spawning the cluster if it's not already spawned.
        """
        # actually start the cluster
        if self.jobflow_id is None:
            self.jobflow_id = provisioning.cluster_start(
                self.created_by.email,
                self.identifier,
                self.size,
                self.public_key
            )

        # set the dates
        if not self.start_date:
            self.start_date = datetime.now().replace(tzinfo=UTC)
        if not self.end_date:
            # clusters should expire after 1 day
            self.end_date = datetime.now().replace(tzinfo=UTC) + timedelta(days=1)

        return super(Cluster, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Remove the cluster from the database, shutting down the actual cluster."""
        if self.jobflow_id is not None:
            provisioning.cluster_stop(self.jobflow_id)

        return super(Cluster, self).delete(*args, **kwargs)


class Worker(models.Model):
    identifier = models.CharField(
        max_length=100,
        help_text="Worker name, used to non-uniqely identify individual workers."
    )
    public_key = models.CharField(
        max_length=100000,
        help_text="Public key that should be authorized for SSH access to the worker."
    )
    start_date = models.DateTimeField(
        blank=True, null=True,
        help_text="Date/time that the worker was started, or null if the worker isn't started yet."
    )
    end_date = models.DateTimeField(
        blank=True, null=True,
        help_text="Date/time that the worker will expire and automatically be killed."
    )
    created_by = models.ForeignKey(
        User, related_name='worker_created_by',
        help_text="User that created the worker instance."
    )
    instance_id = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="AWS EC2 instance ID for the cluster, used for worker management."
    )

    def __str__(self):
        return self.identifier

    def __repr__(self):
        return "<Worker {}>".format(self.identifier)

    def get_info(self):
        return provisioning.worker_info(self.instance_id)

    def save(self, *args, **kwargs):
        # actually start the worker
        if not self.instance_id:
            self.instance_id = provisioning.worker_start(
                self.created_by.email,
                self.identifier,
                self.public_key
            )

        # set the dates
        if not self.start_date:
            self.start_date = datetime.now().replace(tzinfo=UTC)
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=1)  # workers expire after 1 day
        return super(Cluster, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        provisioning.worker_stop(self.worker_id)

        return super(Cluster, self).delete(*args, **kwargs)


class ScheduledSpark(models.Model):
    identifier = models.CharField(
        max_length=100,
        help_text="Job name, used to non-uniqely identify individual jobs."
    )
    notebook_s3_key = models.CharField(
        max_length=800,
        help_text="S3 key of the notebook after uploading it to the Spark code bucket."
    )
    result_visibility = models.CharField(  # can currently be "public" or "private"
        max_length=50,
        help_text="Whether notebook results are uploaded to a public or private bucket"
    )
    size = models.IntegerField(
        help_text="Number of computers to use to run the job."
    )
    interval_in_hours = models.IntegerField(
        help_text="Interval at which the job should run, in hours."
    )
    job_timeout = models.IntegerField(
        help_text="Number of hours before the job times out."
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
        User, related_name='scheduled_spark_created_by',
        help_text="User that created the scheduled job instance."
    )

    current_run_jobflow_id = models.CharField(max_length=50, blank=True, null=True)
    most_recent_status = models.CharField(max_length=50, default="NOT RUNNING")

    def __str__(self):
        return self.identifier

    def __repr__(self):
        return "<ScheduledSpark {} with {} nodes>".format(self.identifier, self.size)

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

    def is_expired(self, at_time = None):
        if self.current_run_jobflow_id is None:
            return False  # job isn't even running at the moment
        if at_time is None:
            at_time = datetime.now().replace(tzinfo=UTC)
        if self.last_run_date + timedelta(hours=self.job_timeout) >= at_time:
            return True  # current job run expired
        return False

    def should_run(self, at_time = None):
        """Return True if the scheduled Spark job should run, False otherwise."""
        if self.current_run_jobflow_id is not None:
            return False  # the job is still running, don't start it again
        if at_time is None:
            at_time = datetime.now().replace(tzinfo=UTC)
        active = self.start_date <= at_time <= self.end_date
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
        self.current_run_jobflow_id = scheduling.scheduled_spark_run(
            self.created_by.email,
            self.identifier,
            self.notebook_s3_key,
            self.result_visibility == "public",
            self.size,
            self.job_timeout
        )
        self.update_status()

    def terminate(self):
        """Stop the currently running scheduled Spark job."""
        if self.current_run_jobflow_id:
            provisioning.cluster_stop(self.current_run_jobflow_id)

    def save(self, notebook_uploadedfile = None, *args, **kwargs):
        if notebook_uploadedfile is not None:  # notebook specified, replace current notebook
            self.notebook_s3_key = scheduling.scheduled_spark_add(
                self.identifier,
                notebook_uploadedfile
            )
        return super(ScheduledSpark, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.terminate()  # make sure to shut down the cluster if it's currently running
        scheduling.scheduled_spark_remove(self.notebook_s3_key)

        super(ScheduledSpark, self).delete(*args, **kwargs)

    @classmethod
    def step_all(cls):
        """Run all the scheduled tasks that are supposed to run."""
        now = datetime.now()
        for scheduled_spark in cls.objects.all():
            if scheduled_spark.should_run(now):
                scheduled_spark.run()
                scheduled_spark.save()
            if scheduled_spark.is_expired(now):
                scheduled_spark.delete()
