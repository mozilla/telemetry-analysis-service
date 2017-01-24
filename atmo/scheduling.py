# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from uuid import uuid4

from django.conf import settings
from django.utils import timezone
import requests

from .aws import emr, s3


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
    return obj


def spark_job_remove(notebook_s3_key):
    s3.delete_object(
        Bucket=settings.AWS_CONFIG['CODE_BUCKET'],
        Key=notebook_s3_key,
    )


def spark_job_run(user_email, identifier, notebook_uri, result_is_public, size,
                  job_timeout, emr_release):
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

    now = timezone.now().isoformat()
    log_uri = 's3://{}/jobs/{}/{}'.format(settings.AWS_CONFIG['LOG_BUCKET'], identifier, now)

    cluster = emr.run_job_flow(
        Name=str(uuid4()),
        LogUri=log_uri,
        ReleaseLabel='emr-{}'.format(emr_release),
        Instances={
            'MasterInstanceType': settings.AWS_CONFIG['MASTER_INSTANCE_TYPE'],
            'SlaveInstanceType': settings.AWS_CONFIG['WORKER_INSTANCE_TYPE'],
            'InstanceCount': size,
            'Ec2KeyName': settings.AWS_CONFIG['EC2_KEY_NAME'],
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
                    '--notebook', 's3://{}/{}'.format(settings.AWS_CONFIG['CODE_BUCKET'],
                                                      notebook_uri),
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
                'Args': ['--timeout', str(job_timeout * 60)]
            }
        }],
        Tags=[
            {'Key': 'Owner', 'Value': user_email},
            {'Key': 'Name', 'Value': identifier},
            {'Key': 'Application', 'Value': settings.AWS_CONFIG['INSTANCE_APP_TAG']},
            {'Key': 'App', 'Value': settings.AWS_CONFIG['ACCOUNTING_APP_TAG']},
            {'Key': 'Type', 'Value': settings.AWS_CONFIG['ACCOUNTING_TYPE_TAG']},
        ],
        VisibleToAllUsers=True,
    )
    return cluster['JobFlowId']


def spark_job_results(identifier, is_public):
    if is_public:
        bucket = settings.AWS_CONFIG['PUBLIC_DATA_BUCKET']
    else:
        bucket = settings.AWS_CONFIG['PRIVATE_DATA_BUCKET']
    prefix = '{}/'.format(identifier)

    results = {}
    list_objects_v2_paginator = s3.get_paginator('list_objects_v2')
    for page in list_objects_v2_paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get('Contents', []):
            try:
                prefix = item['Key'].split('/')[1]
            except IndexError:
                continue
            results.setdefault(prefix, []).append(item['Key'])
    return results
