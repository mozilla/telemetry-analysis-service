# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

import mail_builder
from botocore.exceptions import ClientError
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..celery import celery
from .models import Cluster
from .provisioners import ClusterProvisioner

logger = get_task_logger(__name__)


@celery.task
def deactivate_clusters():
    """Deactivate clusters that have been expired."""
    now = timezone.now()
    deactivated_clusters = []
    for cluster in Cluster.objects.active().filter(expires_at__lte=now):
        with transaction.atomic():
            deactivated_clusters.append([cluster.identifier, cluster.pk])
            # The cluster is expired
            logger.info(
                'Cluster %s (%s) is expired, deactivating.',
                cluster.pk,
                cluster.identifier,
            )
            cluster.deactivate()
    return deactivated_clusters


@celery.task
def send_expiration_mails():
    """Send expiration emails an hour before the cluster expires."""
    deadline = timezone.now() + timedelta(hours=1)
    with transaction.atomic():
        soon_expired = Cluster.objects.select_for_update().active().filter(
            expires_at__lte=deadline,
            expiration_mail_sent=False,
        )
        for cluster in soon_expired:
            with transaction.atomic():
                message = mail_builder.build_message(
                    'atmo/clusters/mails/expiration.mail', {
                        'cluster': cluster,
                        'deadline': deadline,
                        'settings': settings,
                    },
                )
                message.send()
                cluster.expiration_mail_sent = True
                cluster.save()


@celery.task(max_retries=3, bind=True)
def update_master_address(self, cluster_id, force=False):
    """Update the public IP address for the cluster with the given cluster ID"""
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        # quick way out in case this job was called accidently
        if cluster.master_address and not force:
            return
        # first get the cluster info from AWS
        info = cluster.info
        master_address = info.get('public_dns') or ''
        # then store the public IP of the cluster if found in response
        if master_address:
            cluster.master_address = master_address
            cluster.save()
            return master_address
    except ClientError as exc:
        self.retry(
            exc=exc,
            countdown=celery.backoff(self.request.retries),
        )


# This task runs every 5 minutes (300 seconds),
# which fits nicely in the backoff decay of 8 tries total
@celery.task(max_retries=7, bind=True)
def update_clusters(self):
    """
    Update the cluster metadata from AWS for the pending clusters.

    - To be used periodically.
    - Won't update state if not needed.
    - Will queue updating the Cluster's public IP address if needed.
    """
    # only update the cluster info for clusters that are pending
    active_clusters = Cluster.objects.active()

    # Short-circuit for no active clusters (e.g. on weekends)
    if not active_clusters.exists():
        return []

    # get the start dates of the active clusters, set to the start of the day
    # to counteract time differences between atmo and AWS and use the oldest
    # start date to limit the ListCluster API call to AWS
    oldest_created_at = active_clusters.datetimes('created_at', 'day')

    try:
        # build a mapping between jobflow ID and cluster info
        cluster_mapping = {}
        provisioner = ClusterProvisioner()
        cluster_list = provisioner.list(
            created_after=oldest_created_at[0]
        )
        for cluster_info in cluster_list:
            cluster_mapping[cluster_info['jobflow_id']] = cluster_info

        # go through pending clusters and update the state if needed
        updated_clusters = []
        for cluster in active_clusters:
            with transaction.atomic():
                info = cluster_mapping.get(cluster.jobflow_id)
                # ignore if no info was found for some reason,
                # the cluster was deleted in AWS but it wasn't deleted here yet
                if info is None:
                    continue
                # update cluster status
                cluster.sync(info)
                updated_clusters.append(cluster.identifier)

                # if not given enqueue a job to update the public IP address
                # but only if the cluster is running or waiting, so the
                # API call isn't wasted
                if (not cluster.master_address and
                        cluster.most_recent_status in cluster.READY_STATUS_LIST):
                    transaction.on_commit(
                        lambda: update_master_address.delay(cluster.id)
                    )
        return updated_clusters
    except ClientError as exc:
        self.retry(
            exc=exc,
            countdown=celery.backoff(self.request.retries),
        )
