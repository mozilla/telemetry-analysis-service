# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

import urlman
from autorepr import autorepr, autostr
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone

from ..models import CreatedByModel, EditedAtModel
from .provisioners import ClusterProvisioner
from .queries import ClusterQuerySet, EMRReleaseQuerySet


class EMRRelease(EditedAtModel):
    version = models.CharField(
        max_length=50,
        primary_key=True,
    )
    changelog_url = models.TextField(
        help_text='The URL of the changelog with details about the release.',
        default='',
    )
    help_text = models.TextField(
        help_text='Optional help text to show for users when creating a cluster.',
        default='',
    )
    is_active = models.BooleanField(
        help_text='Whether this version should be shown to the user at all.',
        default=True,
    )
    is_experimental = models.BooleanField(
        help_text='Whether this version should be shown to users as experimental.',
        default=False,
    )
    is_deprecated = models.BooleanField(
        help_text='Whether this version should be shown to users as deprecated.',
        default=False,
    )

    objects = EMRReleaseQuerySet.as_manager()

    class Meta:
        ordering = ['-version']
        get_latest_by = 'created_at'
        verbose_name = 'EMR release'
        verbose_name_plural = 'EMR releases'

    __str__ = autostr('{self.version}')

    __repr__ = autorepr(['version', 'is_active', 'is_experimental', 'is_deprecated'])


class EMRReleaseModel(models.Model):
    EMR_RELEASE_HELP = (
        'Different AWS EMR versions have different versions '
        'of software like Hadoop, Spark, etc. '
        'See <a href="'
        'http://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-whatsnew.html"'
        '>what\'s new</a> in each.'
    )
    emr_release = models.ForeignKey(
        EMRRelease,
        verbose_name='EMR release',
        on_delete=models.PROTECT,
        related_name='created_%(class)ss',  # e.g. emr_release.created_clusters.all()
        help_text=EMR_RELEASE_HELP,
    )

    class Meta:
        abstract = True


class Cluster(EMRReleaseModel, CreatedByModel, EditedAtModel):
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
    READY_STATUS_LIST = [
        STATUS_RUNNING,
        STATUS_WAITING,
    ]
    TERMINATED_STATUS_LIST = (
        STATUS_TERMINATED,
    )
    FAILED_STATUS_LIST = (
        STATUS_TERMINATED_WITH_ERRORS,
    )
    FINAL_STATUS_LIST = TERMINATED_STATUS_LIST + FAILED_STATUS_LIST

    STATE_CHANGE_REASON_INTERNAL_ERROR = 'INTERNAL_ERROR'
    STATE_CHANGE_REASON_VALIDATION_ERROR = 'VALIDATION_ERROR'
    STATE_CHANGE_REASON_INSTANCE_FAILURE = 'INSTANCE_FAILURE'
    STATE_CHANGE_REASON_BOOTSTRAP_FAILURE = 'BOOTSTRAP_FAILURE'
    STATE_CHANGE_REASON_USER_REQUEST = 'USER_REQUEST'
    STATE_CHANGE_REASON_STEP_FAILURE = 'STEP_FAILURE'
    STATE_CHANGE_REASON_ALL_STEPS_COMPLETED = 'ALL_STEPS_COMPLETED'
    FAILED_STATE_CHANGE_REASON_LIST = [
        STATE_CHANGE_REASON_INTERNAL_ERROR,
        STATE_CHANGE_REASON_VALIDATION_ERROR,
        STATE_CHANGE_REASON_INSTANCE_FAILURE,
        STATE_CHANGE_REASON_BOOTSTRAP_FAILURE,
        STATE_CHANGE_REASON_STEP_FAILURE,
    ]
    REQUESTED_STATE_CHANGE_REASON_LIST = [
        STATE_CHANGE_REASON_USER_REQUEST,
    ]
    COMPLETED_STATE_CHANGE_REASON_LIST = [
        STATE_CHANGE_REASON_ALL_STEPS_COMPLETED,
    ]
    DEFAULT_SIZE = 1
    DEFAULT_LIFETIME = 8

    identifier = models.CharField(
        max_length=100,
        help_text="Cluster name, used to non-uniqely identify individual clusters."
    )
    size = models.IntegerField(
        help_text="Number of computers used in the cluster."
    )
    lifetime = models.PositiveSmallIntegerField(
        help_text="Lifetime of the cluster after which it's automatically terminated, in hours.",
        default=DEFAULT_LIFETIME,
    )
    lifetime_extension_count = models.PositiveSmallIntegerField(
        help_text="Number of lifetime extensions.",
        default=0,
    )
    ssh_key = models.ForeignKey(
        'keys.SSHKey',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='launched_clusters',  # e.g. ssh_key.launched_clusters.all()
        help_text="SSH key to use when launching the cluster."
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date/time that the cluster will expire and automatically be deleted."
    )
    finished_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date/time when the cluster was terminated or failed."
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
    expiration_mail_sent = models.BooleanField(
        default=False,
        help_text="Whether the expiration mail were sent."
    )

    objects = ClusterQuerySet.as_manager()

    class Meta:
        permissions = [
            ('view_cluster', 'Can view cluster'),
        ]

    class urls(urlman.Urls):

        def detail(self):
            return reverse('clusters-detail', kwargs={'id': self.id})

        def extend(self):
            return reverse('clusters-extend', kwargs={'id': self.id})

        def terminate(self):
            return reverse('clusters-terminate', kwargs={'id': self.id})

    __str__ = autostr('{self.identifier}')

    __repr__ = autorepr([
        'identifier',
        'most_recent_status',
        'size',
        'lifetime',
        'expires_at',
        'lifetime_extension_count',
    ])

    def get_absolute_url(self):
        return self.urls.detail

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
        return self.expires_at <= timezone.now() + timedelta(hours=1)

    @property
    def provisioner(self):
        return ClusterProvisioner()

    @property
    def info(self):
        return self.provisioner.info(self.jobflow_id)

    def update_status(self):
        """Should be called to update latest cluster status in `self.most_recent_status`."""
        info = self.info
        self.most_recent_status = info['state']
        self.master_address = info.get('public_dns') or ''
        end_datetime = info.get('end_datetime')
        if end_datetime is not None:
            self.finished_at = end_datetime

    def save(self, *args, **kwargs):
        """
        Insert the cluster into the database or update it if already present,
        spawning the cluster if it's not already spawned.
        """
        # actually start the cluster
        if self.jobflow_id is None:
            self.jobflow_id = self.provisioner.start(
                user_username=self.created_by.username,
                user_email=self.created_by.email,
                identifier=self.identifier,
                emr_release=self.emr_release.version,
                size=self.size,
                public_key=self.ssh_key.key,
            )
            self.update_status()

        # set the dates
        if not self.expires_at:
            # clusters should expire after the lifetime it's set to
            self.expires_at = timezone.now() + timedelta(hours=self.lifetime)

        super().save(*args, **kwargs)

    def extend(self, hours):
        self.expires_at = models.F('expires_at') + timedelta(hours=hours)
        self.lifetime_extension_count = models.F('lifetime_extension_count') + 1
        self.save()

    def deactivate(self):
        """Shutdown the cluster and update its status accordingly"""
        self.provisioner.stop(self.jobflow_id)
        self.update_status()
        self.save()
