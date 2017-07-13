# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import constance
import pytest
from botocore.stub import ANY, Stubber
from django.conf import settings
from freezegun import freeze_time


@freeze_time('2016-04-05 13:25:47')
@pytest.mark.parametrize("size,use_spot_instances,groups_length", [
    [1, True, 1],
    [10, False, 2],
    [10, True, 2],
])
def test_job_flow_params(mocker, cluster_provisioner, settings, user,
                         size, use_spot_instances, groups_length):
    config = settings.AWS_CONFIG
    identifier = 'test-flow'
    emr_release = '1.0'
    constance.config.AWS_USE_SPOT_INSTANCES = use_spot_instances
    params = cluster_provisioner.job_flow_params(
        user_username=user.username,
        user_email=user.email,
        identifier=identifier,
        emr_release=emr_release,
        size=size,
    )

    assert params['ReleaseLabel'] == 'emr-1.0'
    assert params['LogUri'] == 's3://log-bucket/clusters/test-flow/2016-04-05T13:25:47+00:00'
    assert params['Instances']['Ec2KeyName'] == config['EC2_KEY_NAME']
    assert params['Instances']['KeepJobFlowAliveWhenNoSteps']

    tag_values = [
        ['Owner', user.email],
        ['Name', identifier],
        ['Application', config['INSTANCE_APP_TAG']],
        ['App', config['ACCOUNTING_APP_TAG']],
        ['Type', config['ACCOUNTING_TYPE_TAG']],
    ]

    tags = {}
    for tag in params['Tags']:
        tags[tag['Key']] = tag['Value']

    for name, value in tag_values:
        assert tags[name] == value

    groups = params['Instances']['InstanceGroups']
    assert len(groups) == groups_length
    assert groups[0]['InstanceRole'] == 'MASTER'
    assert groups[0]['InstanceType'] == config['MASTER_INSTANCE_TYPE']
    assert groups[0]['InstanceCount'] == 1

    if groups_length > 1:
        assert groups[1]['InstanceRole'] == 'CORE'
        assert groups[1]['InstanceType'] == config['MASTER_INSTANCE_TYPE']
        assert groups[1]['InstanceCount'] == size
        if use_spot_instances:
            assert groups[1]['Market'] == 'SPOT'
            assert groups[1]['BidPrice'] == str(settings.CONSTANCE_CONFIG['AWS_SPOT_BID_CORE'][0])
        else:
            assert groups[1]['Market'] == 'ON_DEMAND'


def test_spark_job_add(notebook_maker, spark_job_provisioner):
    notebook = notebook_maker()
    identifier = 'test-identifier'
    key = 'jobs/%s/%s' % (identifier, notebook.name)

    stubber = Stubber(spark_job_provisioner.s3)
    response = {
        'Expiration': 'whatever',
        'ETag': '12345',
        'VersionId': '1.0',
    }
    expected_params = {
        'Body': notebook,
        'Bucket': settings.AWS_CONFIG['CODE_BUCKET'],
        'Key': key,
    }
    stubber.add_response('put_object', response, expected_params)

    with stubber:
        result = spark_job_provisioner.add(
            identifier=identifier,
            notebook_file=notebook,
        )
        assert result == key


def test_spark_job_get(spark_job_provisioner):
    key = 's3://test/test-notebook.ipynb'

    stubber = Stubber(spark_job_provisioner.s3)
    response = {
        'Body': 'content',
    }
    expected_params = {
        'Bucket': settings.AWS_CONFIG['CODE_BUCKET'],
        'Key': key,
    }
    stubber.add_response('get_object', response, expected_params)

    with stubber:
        result = spark_job_provisioner.get(key)
        assert result == response


def test_spark_job_remove(spark_job_provisioner):
    key = 's3://test/test-notebook.ipynb'

    stubber = Stubber(spark_job_provisioner.s3)
    response = {'DeleteMarker': False}
    expected_params = {
        'Bucket': settings.AWS_CONFIG['CODE_BUCKET'],
        'Key': key,
    }
    stubber.add_response('delete_object', response, expected_params)

    with stubber:
        spark_job_provisioner.remove(key)


def test_spark_job_results_empty(mocker, spark_job_provisioner):
    mocker.patch.object(
        spark_job_provisioner.s3,
        'list_objects_v2',
        return_value={},
    )

    results = spark_job_provisioner.results('job-identifier', True)
    assert results == {}


@pytest.mark.parametrize('public', [True, False])
def test_spark_job_results(mocker, public, spark_job_provisioner):
    identifier = 'job-identifier'

    def mocked_list_objects(**kwargs):
        is_public = kwargs['Bucket'] == settings.AWS_CONFIG['PUBLIC_DATA_BUCKET']
        pub_prefix = 'pub' if is_public else ''
        return {
            'Contents': [
                {'Key': '%s/logs/%smy-log.txt' % (identifier, pub_prefix)},
                {'Key': '%s/data/%smy-notebook.ipynb' % (identifier, pub_prefix)},
                {'Key': '%s/data/%ssub/artifact.txt' % (identifier, pub_prefix)},
                # won't be in results because of missing prefixes
                {'Key': 'faulty-key.txt'},
            ]
        }
    mocker.patch.object(
        spark_job_provisioner.s3,
        'list_objects_v2',
        mocked_list_objects
    )

    prefix = 'pub' if public else ''

    results = spark_job_provisioner.results(identifier, public)
    assert results == {
        'data': [
            '%s/data/%smy-notebook.ipynb' % (identifier, prefix),
            '%s/data/%ssub/artifact.txt' % (identifier, prefix),
        ],
        'logs': [
            '%s/logs/%smy-log.txt' % (identifier, prefix)
        ]
    }


@freeze_time('2017-02-03 13:48:09')
@pytest.mark.parametrize('is_public', [True, False])
def test_spark_job_run(mocker, is_public, spark_job_provisioner, user):
    identifier = 'test-flow'
    notebook_key = 'notebook.ipynb'
    emr_release = '1.0'
    job_timeout = 60
    size = 1

    stubber = Stubber(spark_job_provisioner.emr)
    response = {'JobFlowId': '12345'}
    expected_params = {
        'Applications': [
            {'Name': 'Spark'},
            {'Name': 'Hive'},
        ],
        'BootstrapActions': [
            {
                'Name': 'setup-telemetry-spark-job',
                'ScriptBootstrapAction': {
                    'Args': [
                        '--timeout', str(job_timeout * 60),
                    ],
                    'Path': spark_job_provisioner.script_uri,
                }
            }
        ],
        'Configurations': ANY,
        'Instances': {
            'Ec2KeyName': spark_job_provisioner.config['EC2_KEY_NAME'],
            'InstanceGroups': [
                {
                    'InstanceCount': size,
                    'InstanceRole': 'MASTER',
                    'InstanceType': (
                        spark_job_provisioner.config['WORKER_INSTANCE_TYPE']
                    ),
                    'Market': 'ON_DEMAND',
                    'Name': 'Master',
                }
            ],
            'KeepJobFlowAliveWhenNoSteps': False,
        },
        'JobFlowRole': constance.config.AWS_SPARK_INSTANCE_PROFILE,
        'LogUri': (
            's3://log-bucket/%s/%s/2017-02-03T13:48:09+00:00' %
            (spark_job_provisioner.log_dir, identifier)
        ),
        'Name': ANY,
        'ReleaseLabel': 'emr-%s' % emr_release,
        'ServiceRole': 'EMR_DefaultRole',
        'Steps': [
            {
                'ActionOnFailure': 'TERMINATE_JOB_FLOW',
                'HadoopJarStep': {
                    'Args': [
                        spark_job_provisioner.batch_uri,
                        '--job-name',
                        identifier,
                        '--notebook',
                        's3://telemetry-analysis-code-2/%s' % notebook_key,
                        '--data-bucket',
                        settings.AWS_CONFIG['PUBLIC_DATA_BUCKET']
                        if is_public
                        else spark_job_provisioner.config['PRIVATE_DATA_BUCKET'],
                    ],
                    'Jar': spark_job_provisioner.jar_uri,
                },
                'Name': 'RunNotebookStep',
            }
        ],
        'Tags': [
            {'Key': 'Owner', 'Value': user.email},
            {'Key': 'Name', 'Value': identifier},
            {'Key': 'Environment', 'Value': 'test'},
            {'Key': 'Application',
             'Value': spark_job_provisioner.config['INSTANCE_APP_TAG']},
            {'Key': 'App',
             'Value': spark_job_provisioner.config['ACCOUNTING_APP_TAG']},
            {'Key': 'Type',
             'Value': spark_job_provisioner.config['ACCOUNTING_TYPE_TAG']},
        ],
        'VisibleToAllUsers': True,
    }
    stubber.add_response('run_job_flow', response, expected_params)

    with stubber:
        jobflow_id = spark_job_provisioner.run(
            user_username=user.username,
            user_email=user.email,
            identifier=identifier,
            emr_release=emr_release,
            size=size,
            notebook_key=notebook_key,
            is_public=is_public,
            job_timeout=job_timeout,
        )
        assert jobflow_id == '12345'
