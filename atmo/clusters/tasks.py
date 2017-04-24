# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

from botocore.exceptions import ClientError
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from .. import email
from ..celery import celery
from .models import Cluster
from .provisioners import ClusterProvisioner

logger = get_task_logger(__name__)


@celery.task
def deactivate_clusters():
    now = timezone.now()
    deactivated_clusters = []
    for cluster in Cluster.objects.active().filter(end_date__lte=now):
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
    deadline = timezone.now() + timedelta(hours=1)
    soon_expired = Cluster.objects.active().filter(
        end_date__lte=deadline,
        expiration_mail_sent=False,
    )
    for cluster in soon_expired:
        with transaction.atomic():
            subject = '[ATMO] Cluster %s is expiring soon!' % cluster.identifier
            body = render_to_string(
                'atmo/clusters/mails/expiration_body.txt', {
                    'cluster': cluster,
                    'deadline': deadline,
                    'site_url': settings.SITE_URL,
                }
            )
            email.send_email(
                to=cluster.created_by.email,
                subject=subject,
                body=body
            )
            cluster.expiration_mail_sent = True
            cluster.save()


@celery.task(max_retries=3)
@celery.autoretry(ClientError)
def update_master_address(cluster_id, force=False):
    """
    Update the public IP address for the cluster with the given cluster ID
    """
    cluster = Cluster.objects.get(id=cluster_id)
    # quick way out in case this job was called accidently
    if cluster.master_address and not force:
        return
    # first get the cluster info from AWS
    info = cluster.get_info()
    master_address = info.get('public_dns') or ''
    # then store the public IP of the cluster if found in response
    if master_address:
        cluster.master_address = master_address
        cluster.save()
        return master_address


@celery.task(max_retries=3)
@celery.autoretry(ClientError)
def update_clusters():
    """
    Update the cluster metadata from AWS for the pending
    clusters.

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
    oldest_start_date = active_clusters.datetimes('start_date', 'day')

    # build a mapping between jobflow ID and cluster info
    cluster_mapping = {}
    provisioner = ClusterProvisioner()
    cluster_list = provisioner.list(
        created_after=oldest_start_date[0]
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

            # don't update the state if it's equal to the already stored state
            if info['state'] == cluster.most_recent_status:
                continue

            # run an UPDATE query for the cluster
            cluster.most_recent_status = info['state']
            cluster.save()

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
