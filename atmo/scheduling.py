# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from uuid import uuid4

from django.conf import settings
import boto3
import requests

emr = boto3.client('emr', region_name=settings.AWS_CONFIG['AWS_REGION'])
ec2 = boto3.client('ec2', region_name=settings.AWS_CONFIG['AWS_REGION'])
s3 = boto3.client('s3', region_name=settings.AWS_CONFIG['AWS_REGION'])


def spark_job_add(identifier, notebook_uploadedfile):
    """
    Upload the notebook file to S3
    """
    key = 'jobs/{}/{}'.format(identifier, notebook_uploadedfile.name)
    s3.put_object(
        Bucket=settings.AWS_CONFIG['CODE_BUCKET'],
        Key=key,
        Body=notebook_uploadedfile
    )
    return key


def spark_job_get(notebook_s3_key):
    obj = s3.get_object(
        Bucket=settings.AWS_CONFIG['CODE_BUCKET'],
        Key=notebook_s3_key,
    )
    return obj['Body'].read()


def spark_job_remove(notebook_s3_key):
    s3.delete_object(
        Bucket=settings.AWS_CONFIG['CODE_BUCKET'],
        Key=notebook_s3_key,
    )


def spark_job_run(user_email, identifier, notebook_uri, result_is_public, size, job_timeout):
    configurations = requests.get(
        'https://s3-{}.amazonaws.com/{}/configuration/configuration.json'.format(
            settings.AWS_CONFIG['AWS_REGION'],
            settings.AWS_CONFIG['SPARK_EMR_BUCKET']
        )
    ).json()
    if result_is_public:
        data_bucket = settings.AWS_CONFIG['PUBLIC_DATA_BUCKET']
    else:
        data_bucket = settings.AWS_CONFIG['PRIVATE_DATA_BUCKET']
    cluster = emr.run_job_flow(
        Name=str(uuid4()),
        ReleaseLabel=settings.AWS_CONFIG['EMR_RELEASE'],
        Instances={
            'MasterInstanceType': settings.AWS_CONFIG['MASTER_INSTANCE_TYPE'],
            'SlaveInstanceType': settings.AWS_CONFIG['SLAVE_INSTANCE_TYPE'],
            'InstanceCount': size,
            'Ec2KeyName': 'mozilla_vitillo',
        },
        JobFlowRole=settings.AWS_CONFIG['SPARK_INSTANCE_PROFILE'],
        ServiceRole='EMR_DefaultRole',
        Applications=[{'Name': 'Spark'}, {'Name': 'Hive'}],
        Configurations=configurations,
        Steps=[{
            'Name': 'RunNotebookStep',
            'ActionOnFailure': 'TERMINATE_JOB_FLOW',
            'HadoopJarStep': {
                'Jar': 's3://{}.elasticmapreduce/libs/script-runner/script-runner.jar'.format(
                    settings.AWS_CONFIG['AWS_REGION']
                ),
                'Args': [
                    's3://{}/steps/batch.sh'.format(settings.AWS_CONFIG['SPARK_EMR_BUCKET']),
                    '--job-name', identifier,
                    '--notebook', notebook_uri,
                    '--data-bucket', data_bucket
                ]
            }
        }],
        BootstrapActions=[{
            'Name': 'setup-telemetry-spark-jobs',
            'ScriptBootstrapAction': {
                'Path': 's3://{}/bootstrap/telemetry.sh'.format(
                    settings.AWS_CONFIG['SPARK_EMR_BUCKET']
                ),
                'Args': ['--timeout', str(job_timeout)]
            }
        }],
        Tags=[
            {'Key': 'Owner', 'Value': user_email},
            {'Key': 'Name', 'Value': identifier},
            {'Key': 'Application', 'Value': settings.AWS_CONFIG['INSTANCE_APP_TAG']},
        ]
    )
    return cluster['JobFlowId']
