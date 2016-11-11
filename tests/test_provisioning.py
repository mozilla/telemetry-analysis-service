# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import datetime

from atmo import provisioning


def test_list_cluster(mocker):
    today = datetime.today()
    list_cluster = mocker.patch('atmo.aws.emr.list_clusters', return_value={
        'Clusters': [
            {
                'Id': 'j-AB1234567890',
                'Name': '79d540f0-08d4-4455-a8a6-b3d6ffb9f9f3',
                'Status': {
                    'State': 'WAITING',
                    'Timeline': {
                        'CreationDateTime': today,
                    }
                },
                'NormalizedInstanceHours': 123
            },
        ],
    })

    cluster_list = provisioning.cluster_list(today)
    assert list_cluster.call_count == 1
    assert cluster_list == [
        {
            'jobflow_id': 'j-AB1234567890',
            'state': 'WAITING',
            'start_time': today,
        },
    ]


def test_list_cluster_pagination(mocker):
    today = datetime.today()
    # first response with pagination marker
    response = {
        'Clusters': [
            {
                'Id': 'j-AB1234567890',
                'Name': '79d540f0-08d4-4455-a8a6-b3d6ffb9f9f3',
                'Status': {
                    'State': 'WAITING',
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

    list_cluster = mocker.patch(
        'atmo.aws.emr.list_clusters',
        side_effect=[response, response2],
    )

    cluster_list = provisioning.cluster_list(today)
    assert list_cluster.call_count == 2

    cluster = {
        'jobflow_id': 'j-AB1234567890',
        'state': 'WAITING',
        'start_time': today,
    }
    # cluster list is the same two times, for each pagination page
    assert cluster_list == [cluster] * 2
