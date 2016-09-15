from datetime import datetime, timedelta
from pytz import UTC

from django.contrib.auth.models import User
from django.db import models

from ..utils import provisioning


# Default release is the last item.
EMR_RELEASES = ('5.0.0', '4.5.0')


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
        help_text="Date/time that the cluster will expire and automatically be deleted."
    )
    created_by = models.ForeignKey(
        User, related_name='cluster_created_by',
        help_text="User that created the cluster instance."
    )

    jobflow_id = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="AWS cluster/jobflow ID for the cluster, used for cluster management."
    )

    emr_release = models.CharField(
        max_length=50, choices=list(zip(*(EMR_RELEASES,) * 2)), default=EMR_RELEASES[-1],
        help_text=('Different EMR versions have different versions '
                   'of software like Hadoop, Spark, etc')
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
                self.public_key,
                self.emr_release
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
