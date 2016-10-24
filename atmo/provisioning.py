# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from uuid import uuid4

from django.conf import settings
import requests

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
        market = 'SPOT' if settings.AWS_CONFIG['USE_SPOT_INSTANCES'] else 'ON_DEMAND'
        core_group = {
            'Name': 'Worker Instances',
            'Market': market,
            'InstanceRole': 'CORE',
            'InstanceType': settings.AWS_CONFIG['WORKER_INSTANCE_TYPE'],
            'InstanceCount': num_instances - 1
        }

        if market == 'SPOT':
            core_group['BidPrice'] = settings.AWS_CONFIG['CORE_SPOT_BID']

        instance_groups.append(core_group)

    cluster = emr.run_job_flow(
        Name=str(uuid4()),
        ReleaseLabel='emr-{}'.format(emr_release),
        Instances={
            'InstanceGroups': instance_groups,
            'Ec2KeyName': 'mozilla_vitillo',
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


def cluster_rename(jobflow_id, new_identifier):
    emr.add_tags(
        ResourceId=jobflow_id,
        Tags=[
            {'Key': 'Name', 'Value': new_identifier},
        ]
    )


def cluster_info(jobflow_id):
    cluster = emr.describe_cluster(ClusterId=jobflow_id)['Cluster']
    creation_time = cluster['Status']['Timeline']['CreationDateTime']
    return {
        'start_time': creation_time,
        'state': cluster['Status']['State'],
        'public_dns': cluster.get('MasterPublicDnsName'),
    }


def cluster_stop(jobflow_id):
    emr.terminate_job_flows(JobFlowIds=[jobflow_id])
