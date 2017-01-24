# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from uuid import uuid4

import constance
import requests
from django.conf import settings
from django.utils import timezone

from .aws import emr


def cluster_start(user_email, identifier, size, public_key, emr_release):
    """
    Given a user's email, a cluster identifier, a worker count, and a user
    public key, spawns a cluster with the desired properties and returns
    the jobflow ID.
    """
    # if the cluster is of size 1, we don't need to have a separate worker
    num_instances = size if size == 1 else size + 1

    # create the cluster/jobflow on Amazon EMR
    configurations = requests.get(
        'https://s3-{}.amazonaws.com/{}/configuration/configuration.json'.format(
            settings.AWS_CONFIG['AWS_REGION'],
            settings.AWS_CONFIG['SPARK_EMR_BUCKET']
        )
    ).json()

    # setup instance groups using spot market for slaves
    instance_groups = [
        {
            'Name': 'Master',
            'Market': 'ON_DEMAND',
            'InstanceRole': 'MASTER',
            'InstanceType': settings.AWS_CONFIG['MASTER_INSTANCE_TYPE'],
            'InstanceCount': 1
        }
    ]

    if num_instances > 1:
        market = 'SPOT' if constance.config.AWS_USE_SPOT_INSTANCES else 'ON_DEMAND'
        core_group = {
            'Name': 'Worker Instances',
            'Market': market,
            'InstanceRole': 'CORE',
            'InstanceType': settings.AWS_CONFIG['WORKER_INSTANCE_TYPE'],
            'InstanceCount': num_instances - 1
        }

        if market == 'SPOT':
            core_group['BidPrice'] = str(constance.config.AWS_SPOT_BID_CORE)

        instance_groups.append(core_group)

    now = timezone.now().isoformat()
    log_uri = 's3://{}/clusters/{}/{}'.format(settings.AWS_CONFIG['LOG_BUCKET'], identifier, now)

    cluster = emr.run_job_flow(
        Name=str(uuid4()),
        LogUri=log_uri,
        ReleaseLabel='emr-{}'.format(emr_release),
        Instances={
            'InstanceGroups': instance_groups,
            'Ec2KeyName': settings.AWS_CONFIG['EC2_KEY_NAME'],
            'KeepJobFlowAliveWhenNoSteps': True,  # same as no-auto-terminate
        },
        JobFlowRole=settings.AWS_CONFIG['SPARK_INSTANCE_PROFILE'],
        ServiceRole='EMR_DefaultRole',
        Applications=[{'Name': 'Spark'}, {'Name': 'Hive'}],
        Configurations=configurations,
        BootstrapActions=[{
            'Name': 'setup-telemetry-cluster',
            'ScriptBootstrapAction': {
                'Path': 's3://{}/bootstrap/telemetry.sh'.format(
                    settings.AWS_CONFIG['SPARK_EMR_BUCKET']
                ),
                'Args': ['--public-key', public_key]
            }
        }],
        Tags=[
            {'Key': 'Owner', 'Value': user_email},
            {'Key': 'Name', 'Value': identifier},
            {'Key': 'Application', 'Value': settings.AWS_CONFIG['INSTANCE_APP_TAG']},
            {'Key': 'App', 'Value': settings.AWS_CONFIG['ACCOUNTING_APP_TAG']},
            {'Key': 'Type', 'Value': settings.AWS_CONFIG['ACCOUNTING_TYPE_TAG']},
        ],
        VisibleToAllUsers=True
    )

    return cluster['JobFlowId']


def cluster_info(jobflow_id):
    """
    Retun the cluster info for the cluster with the given Jobflow ID
    with the fields start time, state and public IP address
    """
    cluster = emr.describe_cluster(ClusterId=jobflow_id)['Cluster']
    creation_time = cluster['Status']['Timeline']['CreationDateTime']
    return {
        'start_time': creation_time,
        'state': cluster['Status']['State'],
        'public_dns': cluster.get('MasterPublicDnsName'),
    }


def cluster_list(created_after, created_before=None):
    """
    Return a list of cluster infos in the given time frame with the fields:
    - Jobflow ID
    - state
    - start time
    """
    # set some parameters so we don't get *all* clusters ever
    params = {'CreatedAfter': created_after}
    if created_before is not None:
        params['CreatedBefore'] = created_before

    clusters = []
    list_cluster_paginator = emr.get_paginator('list_clusters')
    for page in list_cluster_paginator.paginate(**params):
        for cluster in page.get('Clusters', []):
            clusters.append({
                'jobflow_id': cluster['Id'],
                'state': cluster['Status']['State'],
                'start_time': cluster['Status']['Timeline']['CreationDateTime'],
            })
    return clusters


def cluster_stop(jobflow_id):
    emr.terminate_job_flows(JobFlowIds=[jobflow_id])
