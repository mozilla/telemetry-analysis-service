# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

from django.core.urlresolvers import reverse
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .. import provisioning


class Cluster(models.Model):
    FINAL_STATUS_LIST = ('COMPLETED', 'TERMINATED', 'FAILED')
    # Default release is the first item, order should be from latest to oldest
    EMR_RELEASES = (
        '5.0.0',
        '4.5.0',
    )
    EMR_RELEASES_CHOICES = list(zip(*(EMR_RELEASES,) * 2))
    EMR_RELEASES_CHOICES_DEFAULT = EMR_RELEASES[0]

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
        max_length=50, choices=EMR_RELEASES_CHOICES, default=EMR_RELEASES_CHOICES_DEFAULT,
        help_text=('Different EMR versions have different versions '
                   'of software like Hadoop, Spark, etc')
    )

    most_recent_status = models.CharField(
        max_length=50, default="UNKNOWN",
        help_text="Most recently retrieved AWS status for the cluster."
    )
    master_address = models.CharField(
        max_length=255, default="", blank=True,
        help_text=("Public address of the master node."
                   "This is only available once the cluster has bootstrapped")
    )

    def __str__(self):
        return self.identifier

    def __repr__(self):
        return "<Cluster {} of size {}>".format(self.identifier, self.size)

    def get_info(self):
        return provisioning.cluster_info(self.jobflow_id)

    def update_status(self):
        """Should be called to update latest cluster status in `self.most_recent_status`."""
        info = self.get_info()
        self.most_recent_status = info['state']
        self.master_address = info.get('public_dns') or ''

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
            self.update_status()

        # set the dates
        now = timezone.now()
        if not self.start_date:
            self.start_date = now
        if not self.end_date:
            # clusters should expire after 1 day
            self.end_date = now + timedelta(days=1)

        return super(Cluster, self).save(*args, **kwargs)

    def deactivate(self):
        """Shutdown the cluster and update its status accordingly"""
        provisioning.cluster_stop(self.jobflow_id)
        self.update_status()
        self.save()

    @property
    def is_active(self):
        return self.most_recent_status not in self.FINAL_STATUS_LIST

    @property
    def is_terminating(self):
        return self.most_recent_status == 'TERMINATING'

    @property
    def is_ready(self):
        return self.most_recent_status == 'WAITING'

    @property
    def is_expiring_soon(self):
        """Returns true if the cluster is expiring in the next hour."""
        return self.end_date <= timezone.now() + timedelta(hours=1)

    def get_absolute_url(self):
        return reverse('clusters-detail', kwargs={'id': self.id})
