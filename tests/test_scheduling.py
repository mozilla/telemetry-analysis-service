# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf import settings
import pytest
from atmo.aws import s3
from atmo.scheduling import get_spark_job_results


def test_get_spark_job_results_empty(mocker):
    mocker.patch.object(s3, 'list_objects_v2', return_value={})

    results = get_spark_job_results('job-identifier', True)
    assert results == {}


@pytest.mark.parametrize('public', [True, False])
def test_get_spark_job_results(mocker, public):
    identifier = 'job-identifier'

    def mocked_list_objects(**kwargs):
        is_public = kwargs['Bucket'] == settings.AWS_CONFIG['PUBLIC_DATA_BUCKET']
        pub_prefix = 'pub' if is_public else ''
        return {
            'Contents': [
                {'Key': '{}/logs/{}my-log.txt'.format(identifier, pub_prefix)},
                {'Key': '{}/data/{}my-notebook.ipynb'.format(identifier, pub_prefix)},
                {'Key': '{}/data/{}sub/artifact.txt'.format(identifier, pub_prefix)},
            ]
        }
    mocker.patch.object(s3, 'list_objects_v2', mocked_list_objects)

    prefix = 'pub' if public else ''

    results = get_spark_job_results(identifier, public)
    assert results == {
        'data': [
            '{}/data/{}my-notebook.ipynb'.format(identifier, prefix),
            '{}/data/{}sub/artifact.txt'.format(identifier, prefix),
        ],
        'logs': [
            '{}/logs/{}my-log.txt'.format(identifier, prefix)
        ]
    }
