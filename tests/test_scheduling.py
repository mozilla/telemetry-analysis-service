# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf import settings
import pytest

from atmo.aws import s3
from atmo import scheduling


def test_spark_job_add(mocker, notebook_maker):
    s3_put_object = mocker.patch('atmo.aws.s3.put_object')
    notebook = notebook_maker()
    identifier = 'test-identifier'
    key = 'jobs/{}/{}'.format(identifier, notebook.name)

    result = scheduling.spark_job_add(identifier, notebook)
    assert result == key
    s3_put_object.assert_called_with(
        Body=notebook,
        Bucket=settings.AWS_CONFIG['CODE_BUCKET'],
        Key=key
    )


def test_spark_job_get(mocker):
    response = {'some': 'keys'}  # using some dumbed down response here by design
    s3_get_object = mocker.patch('atmo.aws.s3.get_object', return_value=response)
    key = 's3://test/test-notebook.ipynb'
    result = scheduling.spark_job_get(key)
    s3_get_object.assert_called_with(
        Bucket=settings.AWS_CONFIG['CODE_BUCKET'],
        Key=key,
    )
    assert result == response


def test_spark_job_remove(mocker):
    response = {'DeleteMarker': False}
    s3_delete_object = mocker.patch('atmo.aws.s3.delete_object', return_value=response)
    key = 's3://test/test-notebook.ipynb'
    scheduling.spark_job_remove(key)
    s3_delete_object.assert_called_with(
        Bucket=settings.AWS_CONFIG['CODE_BUCKET'],
        Key=key,
    )


def test_spark_job_results_empty(mocker):
    mocker.patch.object(s3, 'list_objects_v2', return_value={})

    results = scheduling.spark_job_results('job-identifier', True)
    assert results == {}


@pytest.mark.parametrize('public', [True, False])
def test_spark_job_results(mocker, public):
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

    results = scheduling.spark_job_results(identifier, public)
    assert results == {
        'data': [
            '{}/data/{}my-notebook.ipynb'.format(identifier, prefix),
            '{}/data/{}sub/artifact.txt'.format(identifier, prefix),
        ],
        'logs': [
            '{}/logs/{}my-log.txt'.format(identifier, prefix)
        ]
    }
