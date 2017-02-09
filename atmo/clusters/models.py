# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

from django.db import models
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible

from .provisioners import ClusterProvisioner
from ..models import CreatedByModel, EMRReleaseModel


class ClusterManager(models.Manager):

    def active(self):
        return self.filter(
            most_recent_status__in=Cluster.ACTIVE_STATUS_LIST,
        )

    def terminated(self):
        return self.filter(
            most_recent_status__in=Cluster.TERMINATED_STATUS_LIST,
        )

    def failed(self):
        return self.filter(
            most_recent_status__in=Cluster.FAILED_STATUS_LIST,
        )


@python_2_unicode_compatible
class Cluster(EMRReleaseModel, CreatedByModel):
    STATUS_STARTING = 'STARTING'
    STATUS_BOOTSTRAPPING = 'BOOTSTRAPPING'
    STATUS_RUNNING = 'RUNNING'
    STATUS_WAITING = 'WAITING'
    STATUS_TERMINATING = 'TERMINATING'
    STATUS_TERMINATED = 'TERMINATED'
    STATUS_TERMINATED_WITH_ERRORS = 'TERMINATED_WITH_ERRORS'

    ACTIVE_STATUS_LIST = (
        STATUS_STARTING,
        STATUS_BOOTSTRAPPING,
        STATUS_RUNNING,
        STATUS_WAITING,
        STATUS_TERMINATING,
    )
    TERMINATED_STATUS_LIST = (
        STATUS_TERMINATED,
    )
    FAILED_STATUS_LIST = (
        STATUS_TERMINATED_WITH_ERRORS,
    )

    identifier = models.CharField(
        max_length=100,
        help_text="Cluster name, used to non-uniqely identify individual clusters."
    )
    size = models.IntegerField(
        help_text="Number of computers  used in the cluster."
    )
    ssh_key = models.ForeignKey(
        'keys.SSHKey',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='launched_clusters',  # e.g. ssh_key.launched_clusters.all()
        help_text="SSH key to use when launching the cluster."
    )
    start_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date/time that the cluster was started, or null if it isn't started yet."
    )
    end_date = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date/time that the cluster will expire and automatically be deleted."
    )

    jobflow_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="AWS cluster/jobflow ID for the cluster, used for cluster management."
    )

    most_recent_status = models.CharField(
        max_length=50,
        default='',
        blank=True,
        help_text="Most recently retrieved AWS status for the cluster."
    )
    master_address = models.CharField(
        max_length=255,
        default='',
        blank=True,
        help_text=("Public address of the master node."
                   "This is only available once the cluster has bootstrapped")
    )

    expiration_mail_sent = models.BooleanField(default=False)

    objects = ClusterManager()

    class Meta:
        permissions = [
            ('view_cluster', 'Can view cluster'),
        ]

    def __str__(self):
        return self.identifier

    def __repr__(self):
        return "<Cluster {} of size {}>".format(self.identifier, self.size)

    @property
    def is_active(self):
        return self.most_recent_status in self.ACTIVE_STATUS_LIST

    @property
    def is_terminated(self):
        return self.most_recent_status in self.TERMINATED_STATUS_LIST

    @property
    def is_failed(self):
        return self.most_recent_status in self.FAILED_STATUS_LIST

    @property
    def is_terminating(self):
        return self.most_recent_status == self.STATUS_TERMINATING

    @property
    def is_ready(self):
        return self.most_recent_status == self.STATUS_WAITING

    @property
    def is_expiring_soon(self):
        """Returns true if the cluster is expiring in the next hour."""
        return self.end_date <= timezone.now() + timedelta(hours=1)

    @property
    def provisioner(self):
        return ClusterProvisioner()

    def get_absolute_url(self):
        return reverse('clusters-detail', kwargs={'id': self.id})

    def get_info(self):
        return self.provisioner.info(self.jobflow_id)

    def update_status(self):
        """Should be called to update latest cluster status in `self.most_recent_status`."""
        info = self.get_info()
        self.most_recent_status = info['state']
        self.master_address = info.get('public_dns') or ''

    def save(self, *args, **kwargs):
        """
        Insert the cluster into the database or update it if already present,
        spawning the cluster if it's not already spawned.
        """
        # actually start the cluster
        if self.jobflow_id is None:
            self.jobflow_id = self.provisioner.start(
                user_email=self.created_by.email,
                identifier=self.identifier,
                emr_release=self.emr_release,
                size=self.size,
                public_key=self.ssh_key.key,
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
        self.provisioner.stop(self.jobflow_id)
        self.update_status()
        self.save()
