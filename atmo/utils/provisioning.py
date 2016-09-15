from uuid import uuid4
from io import BytesIO

from django.conf import settings
from django.template.loader import render_to_string
import boto3
import requests

emr = boto3.client('emr', region_name=settings.AWS_CONFIG['AWS_REGION'])
ec2 = boto3.client('ec2', region_name=settings.AWS_CONFIG['AWS_REGION'])
s3 = boto3.client('s3', region_name=settings.AWS_CONFIG['AWS_REGION'])


def cluster_start(user_email, identifier, size, public_key, emr_release):
    '''Given a user's email, a cluster identifier, a worker count, and a user public key,
    spawns a cluster with the desired properties and returns the jobflow ID.'''
    # if the cluster is of size 1, we don't need to have a separate worker
    num_instances = size if size == 1 else size + 1

    # create the cluster/jobflow on Amazon EMR
    configurations = requests.get(
        'https://s3-{}.amazonaws.com/{}/configuration/configuration.json'.format(
            settings.AWS_CONFIG['AWS_REGION'],
            settings.AWS_CONFIG['SPARK_EMR_BUCKET']
        )
    ).json()
    cluster = emr.run_job_flow(
        Name=str(uuid4()),
        ReleaseLabel='emr-{}'.format(emr_release),
        Instances={
            'MasterInstanceType': settings.AWS_CONFIG['INSTANCE_TYPE'],
            'SlaveInstanceType': settings.AWS_CONFIG['INSTANCE_TYPE'],
            'InstanceCount': num_instances,
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
        'state':      cluster['Status']['State'],
        'public_dns': cluster['MasterPublicDnsName'],
    }


def cluster_stop(jobflow_id):
    emr.terminate_job_flows(JobFlowIds=[jobflow_id])


def worker_start(user_email, identifier, public_key):
    # upload the public key to S3
    token = str(uuid4())
    s3_key = 'keys/{}.pub'.format(token)
    s3.put_object(
        Bucket = settings.AWS_CONFIG['CODE_BUCKET'],
        Key = s3_key,
        Body = BytesIO(public_key)
    )

    # generate the boot script for the worker
    ephemeral_map = settings.AWS_CONFIG.get('EPHEMERAL_MAP', {})
    boot_script = render_to_string('boot-script.sh', context={
        'aws_region':       settings.AWS_CONFIG['AWS_REGION'],
        'temporary_bucket': settings.AWS_CONFIG['CODE_BUCKET'],
        'ssh_key':          s3_key,
        'ephemeral_map':    ephemeral_map,
    })

    # generate the ephemeral storage mapping
    mapping = [
        {'DeviceName': device, 'VirtualName': ephemeral_name}
        for device, ephemeral_name in ephemeral_map.iteritems()
    ]

    # create a new worker EC2 instance with the
    # "ubuntu/images/hvm/ubuntu-vivid-15.04-amd64-server-20151006" image
    reservation = ec2.run_instances(
        ImageId                           = 'ami-2cfe1a1f',
        SecurityGroups                    = settings.AWS_CONFIG['SECURITY_GROUPS'],
        UserData                          = boot_script,
        BlockDeviceMappings               = mapping,
        InstanceType                      = settings.AWS_CONFIG['INSTANCE_TYPE'],
        InstanceInitiatedShutdownBehavior = 'terminate',
        ClientToken                       = token,
        IamInstanceProfile                = {'Name': settings.AWS_CONFIG['INSTANCE_PROFILE']}
    )
    instance_id = reservation['Instances'][0]['InstanceId']

    # associate the EC2 instance with the user who launched it, the instance identifier,
    # and the Telemetry Analysis tag
    ec2.create_tags(
        DryRun=False,
        Resources=[instance_id],
        Tags=[
            {'Key': 'Owner', 'Value': user_email},
            {'Key': 'Name', 'Value': identifier},
            {'Key': 'Application', 'Value': settings.AWS_CONFIG['INSTANCE_APP_TAG']},
        ]
    )

    return instance_id


def worker_info(instance_id):
    worker = ec2.describe_instances(
        DryRun=False,
        InstanceIds=[instance_id]
    )['Reservations'][0]['Instances'][0]
    creation_time = worker['LaunchTime']
    return {
        'start_time': creation_time,
        'state':      worker['State']['Name'],
        'public_dns': worker['PublicDnsName'],
    }


def worker_stop(instance_id):
    ec2.terminate_instances(
        DryRun=False,
        InstanceIds=[instance_id]
    )


def get_tag_value(tags, key):
    '''Useful utility function that retrieves the value of a tag list generated by Boto.'''
    return next((tag.value for tag in tags if tag.key == key), None)
