# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime

import constance
from botocore.stub import ANY, Stubber
from freezegun import freeze_time

from atmo.provisioners import Provisioner


def test_spark_emr_configuration(mocker):
    provisioner = Provisioner()
    mocker.stopall()
    mock_get = mocker.patch.object(provisioner.session, 'get')
    provisioner.spark_emr_configuration()
    mock_get.assert_called_with(provisioner.spark_emr_configuration_url)


@freeze_time('2017-02-03 13:48:09')
def test_cluster_start(mocker, cluster_provisioner, ssh_key, user):
    identifier = 'test-flow'
    emr_release = '5.0.0'
    size = 1
    public_key = ssh_key.key

    stubber = Stubber(cluster_provisioner.emr)
    response = {'JobFlowId': '12345'}
    expected_params = {
        'Applications': [
            {'Name': 'Spark'},
            {'Name': 'Hive'},
            {'Name': 'Zeppelin'}
        ],
        'BootstrapActions': [
            {
                'Name': 'setup-telemetry-cluster',
                'ScriptBootstrapAction': {
                    'Args': [
                        '--public-key', public_key,
                        '--email', user.email,
                        '--efs-dns', constance.config.AWS_EFS_DNS,
                    ],
                    'Path': cluster_provisioner.script_uri,
                }
            }
        ],
        'Configurations': ANY,
        'Instances': {
            'Ec2KeyName': cluster_provisioner.config['EC2_KEY_NAME'],
            'InstanceGroups': [
                {
                    'InstanceCount': size,
                    'InstanceRole': 'MASTER',
                    'InstanceType': cluster_provisioner.config['WORKER_INSTANCE_TYPE'],
                    'Market': 'ON_DEMAND',
                    'Name': 'Master',
                }
            ],
            'KeepJobFlowAliveWhenNoSteps': True,
        },
        'JobFlowRole': constance.config.AWS_SPARK_INSTANCE_PROFILE,
        'LogUri': (
            's3://log-bucket/%s/%s/2017-02-03T13:48:09+00:00' %
            (cluster_provisioner.log_dir, identifier)
        ),
        'Name': ANY,
        'ReleaseLabel': 'emr-%s' % emr_release,
        'ServiceRole': 'EMR_DefaultRole',
        'Steps': [
            {
                'ActionOnFailure': 'TERMINATE_JOB_FLOW',
                'HadoopJarStep': {
                    'Args': [
                        cluster_provisioner.zeppelin_uri
                    ],
                    'Jar': cluster_provisioner.jar_uri
                },
                'Name': 'setup-zeppelin'
            }
        ],
        'Tags': [
            {'Key': 'Owner', 'Value': user.email},
            {'Key': 'Name', 'Value': identifier},
            {'Key': 'Environment', 'Value': 'test'},
            {'Key': 'Application', 'Value': cluster_provisioner.config['INSTANCE_APP_TAG']},
            {'Key': 'App', 'Value': cluster_provisioner.config['ACCOUNTING_APP_TAG']},
            {'Key': 'Type', 'Value': cluster_provisioner.config['ACCOUNTING_TYPE_TAG']},
        ],
        'VisibleToAllUsers': True,
    }
    stubber.add_response('run_job_flow', response, expected_params)

    with stubber:
        jobflow_id = cluster_provisioner.start(
            user_username=user.username,
            user_email=user.email,
            identifier=identifier,
            emr_release=emr_release,
            size=size,
            public_key=public_key,
        )
        assert jobflow_id == '12345'


def test_list_cluster(mocker, cluster_provisioner):
    today = datetime.today()
    list_cluster = mocker.patch.object(
        cluster_provisioner.emr,
        'list_clusters',
        return_value={
            'Clusters': [
                {
                    'Id': 'j-AB1234567890',
                    'Name': '79d540f0-08d4-4455-a8a6-b3d6ffb9f9f3',
                    'Status': {
                        'State': 'WAITING',
                        'StateChangeReason': {
                            'Code': 'ALL_STEPS_COMPLETED',
                            'Message': 'All steps completed.',
                        },
                        'Timeline': {
                            'CreationDateTime': today,
                        }
                    },
                    'NormalizedInstanceHours': 123
                },
            ],
        }
    )

    cluster_list = cluster_provisioner.list(today)
    assert list_cluster.call_count == 1
    assert cluster_list == [
        {
            'jobflow_id': 'j-AB1234567890',
            'state': 'WAITING',
            'state_change_reason_code': 'ALL_STEPS_COMPLETED',
            'state_change_reason_message': 'All steps completed.',
            'creation_datetime': today,
            'ready_datetime': None,
            'end_datetime': None,
        },
    ]


def test_list_cluster_pagination(mocker, cluster_provisioner):
    today = datetime.today()
    # first response with pagination marker
    response = {
        'Clusters': [
            {
                'Id': 'j-AB1234567890',
                'Name': '79d540f0-08d4-4455-a8a6-b3d6ffb9f9f3',
                'Status': {
                    'State': 'WAITING',
                    'StateChangeReason': {
                        'Code': 'ALL_STEPS_COMPLETED',
                        'Message': 'All steps completed.',
                    },
                    'Timeline': {
                        'CreationDateTime': today,
                    }
                },
                'NormalizedInstanceHours': 123
            },
        ],
        'Marker': 'some-marker',
    }
    # second response without the marker
    response2 = response.copy()
    response2.pop('Marker')

    list_cluster = mocker.patch.object(
        cluster_provisioner.emr,
        'list_clusters',
        side_effect=[response, response2],
    )

    cluster_list = cluster_provisioner.list(today)
    assert list_cluster.call_count == 2

    cluster = {
        'jobflow_id': 'j-AB1234567890',
        'state': 'WAITING',
        'state_change_reason_code': 'ALL_STEPS_COMPLETED',
        'state_change_reason_message': 'All steps completed.',
        'creation_datetime': today,
        'ready_datetime': None,
        'end_datetime': None,
    }
    # cluster list is the same two times, for each pagination page
    assert cluster_list == [cluster] * 2


def test_stop_cluster(cluster_provisioner):
    stubber = Stubber(cluster_provisioner.emr)
    response = {}
    expected_params = {
        'JobFlowIds': ['12345'],
    }
    stubber.add_response('terminate_job_flows', response, expected_params)

    with stubber:
        cluster_provisioner.stop(jobflow_id='12345')


def test_create_cluster_valid_parameters(cluster_provisioner):
    """Test that the parameters passed down to run_job_flow are valid"""

    stubber = Stubber(cluster_provisioner.emr)
    response = {'JobFlowId': 'job-flow-id'}
    stubber.add_response('run_job_flow', response)

    emr_release = '5.0.0'
    with stubber:
        jobflow_id = cluster_provisioner.start(
            user_username='user',
            user_email='user@example.com',
            identifier='cluster',
            emr_release=emr_release,
            size=3,
            public_key='public-key',
        )

    assert jobflow_id == response['JobFlowId']


def test_cluster_info(cluster_provisioner):
    cluster_id = 'foo-bar-spam-egs'
    stubber = Stubber(cluster_provisioner.emr)
    response = {
        'Cluster': {
            'MasterPublicDnsName': '1.2.3.4',
            'Status': {
                'State': 'RUNNING',
                'StateChangeReason': {
                    'Code': 'ALL_STEPS_COMPLETED',
                    'Message': 'All steps completed.',
                },
                'Timeline': {
                    'CreationDateTime': datetime(2015, 1, 1),
                    'ReadyDateTime': datetime(2015, 1, 2),
                    'EndDateTime': datetime(2015, 1, 3),
                }
            },
        },
    }
    expected_params = {'ClusterId': cluster_id}
    stubber.add_response('describe_cluster', response, expected_params)

    with stubber:
        info = cluster_provisioner.info(cluster_id)
        assert info == {
            'creation_datetime': datetime(2015, 1, 1),
            'ready_datetime': datetime(2015, 1, 2),
            'end_datetime': datetime(2015, 1, 3),
            'state_change_reason_code': 'ALL_STEPS_COMPLETED',
            'state_change_reason_message': 'All steps completed.',
            'state': 'RUNNING',
            'public_dns': '1.2.3.4',
        }


def test_cluster_list(cluster_provisioner):
    created_after = datetime(1970, 1, 1)
    created_before = datetime(2020, 1, 1)

    stubber = Stubber(cluster_provisioner.emr)
    response = {
        'Clusters': [
            {
                'Id': 'cluster-1',
                'Status': {
                    'State': 'TERMINATED',
                    'StateChangeReason': {
                        'Code': 'ALL_STEPS_COMPLETED',
                        'Message': 'All steps completed.',
                    },
                    'Timeline': {
                        'CreationDateTime': datetime(2015, 1, 1),
                        'ReadyDateTime': datetime(2015, 1, 2),
                        'EndDateTime': datetime(2015, 1, 3),
                    }
                },
            },
            {
                'Id': 'cluster-2',
                'Status': {
                    'State': 'RUNNING',
                    'StateChangeReason': {
                        'Code': 'ALL_STEPS_COMPLETED',
                        'Message': 'All steps completed.',
                    },
                    'Timeline': {
                        'CreationDateTime': datetime(2016, 1, 1),
                        'ReadyDateTime': datetime(2016, 1, 2),
                        'EndDateTime': datetime(2016, 1, 3),
                    }
                },
            },
        ],
    }
    expected_params = {
        'CreatedAfter': created_after,
    }
    expected_result = [
        {
            'creation_datetime': datetime(2015, 1, 1),
            'ready_datetime': datetime(2015, 1, 2),
            'end_datetime': datetime(2015, 1, 3),
            'state': 'TERMINATED',
            'state_change_reason_code': 'ALL_STEPS_COMPLETED',
            'state_change_reason_message': 'All steps completed.',
            'jobflow_id': 'cluster-1',
        },
        {
            'creation_datetime': datetime(2016, 1, 1),
            'ready_datetime': datetime(2016, 1, 2),
            'end_datetime': datetime(2016, 1, 3),
            'state': 'RUNNING',
            'state_change_reason_code': 'ALL_STEPS_COMPLETED',
            'state_change_reason_message': 'All steps completed.',
            'jobflow_id': 'cluster-2',
        },
    ]
    stubber.add_response('list_clusters', response, expected_params)
    with stubber:

        info = cluster_provisioner.list(created_after)
        assert info == expected_result

    # with created_before
    expected_params = {
        'CreatedAfter': created_after,
        'CreatedBefore': created_before,
    }
    stubber.add_response('list_clusters', response, expected_params)

    with stubber:
        info = cluster_provisioner.list(
            created_after,
            created_before=created_before,
        )
        assert info == expected_result
