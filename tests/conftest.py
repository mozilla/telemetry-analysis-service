# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import io
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.management import call_command
from django.utils import timezone
from django_redis import get_redis_connection
from pytest_factoryboy import register as factory_register

from atmo.clusters.factories import ClusterFactory, EMRReleaseFactory
from atmo.clusters.models import Cluster
from atmo.clusters.provisioners import ClusterProvisioner
from atmo.jobs.factories import (SparkJobFactory, SparkJobRunFactory,
                                 SparkJobWithRunFactory)
from atmo.jobs.provisioners import SparkJobProvisioner
from atmo.keys.factories import SSHKeyFactory
from atmo.users.factories import GroupFactory, UserFactory


pytest_plugins = ['blockade', 'messages']


def pytest_addoption(parser):
    parser.addoption(
        '--staticfiles',
        action='store_true',
        dest='staticfiles',
        help='Collect Django staticfiles',
    )
    parser.addoption(
        '--no-staticfiles',
        action='store_false',
        dest='staticfiles',
        help="Don't collect Django staticfiles",
    )


factory_register(ClusterFactory)
factory_register(EMRReleaseFactory)
factory_register(SparkJobFactory)
factory_register(SparkJobRunFactory)
factory_register(SparkJobWithRunFactory, 'spark_job_with_run')
factory_register(SSHKeyFactory)
factory_register(UserFactory)
factory_register(UserFactory, 'user2')
factory_register(GroupFactory)


@pytest.fixture(scope='session', autouse=True)
def collectstatic(request):
    if request.config.getoption('--staticfiles'):
        call_command(
            'collectstatic',
            link=True,
            verbosity=2,
            interactive=False,
        )


@pytest.fixture(autouse=True)
def flushall_redis():
    get_redis_connection().flushall()


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass


@pytest.fixture
def now():
    return timezone.now().replace(microsecond=0)


@pytest.fixture
def one_hour_ago(now):
    return now - timedelta(hours=1)


@pytest.fixture
def one_hour_ahead(now):
    return now + timedelta(hours=1)


@pytest.fixture
def client(client, user):
    """
    Overriding the default test client to have a user logged in automatically.
    """
    client.force_login(user)
    return client


@pytest.fixture
def notebook_maker():
    def maker(extension='ipynb'):
        return InMemoryUploadedFile(
            file=io.BytesIO(b'{}'),
            field_name='notebook',
            name='test-notebook.%s' % extension,
            content_type='text/plain',
            size=2,
            charset='utf8',
        )
    return maker


@pytest.fixture
def cluster_provisioner_mocks(mocker):
    return {
        'start': mocker.patch(
            'atmo.clusters.provisioners.ClusterProvisioner.start',
            return_value='12345',
        ),
        'stop': mocker.patch(
            'atmo.clusters.provisioners.ClusterProvisioner.stop',
            return_value=None,
        ),
        'info': mocker.patch(
            'atmo.clusters.provisioners.ClusterProvisioner.info',
            return_value={
                'creation_datetime': timezone.now(),
                'ready_datetime': None,
                'end_datetime': None,
                'state': Cluster.STATUS_BOOTSTRAPPING,
                'state_change_reason_code': None,
                'state_change_reason_message': None,
                'public_dns': 'master.public.dns.name',
            },
        )
    }


@pytest.fixture
def cluster_provisioner(settings):
    settings.AWS_CONFIG['LOG_BUCKET'] = 'log-bucket'
    return ClusterProvisioner()


@pytest.fixture
def spark_job_provisioner(settings):
    settings.AWS_CONFIG['LOG_BUCKET'] = 'log-bucket'
    return SparkJobProvisioner()


@pytest.fixture
def sparkjob_provisioner_mocks(mocker):
    return {
        'get': mocker.patch(
            'atmo.jobs.provisioners.SparkJobProvisioner.get',
            return_value={
                'Body': io.BytesIO(b'content'),
                'ContentLength': 7,
            }
        ),
        'add': mocker.patch(
            'atmo.jobs.provisioners.SparkJobProvisioner.add',
            return_value='jobs/test-spark-job/test-notebook.ipynb',
        ),
        'results': mocker.patch(
            'atmo.jobs.provisioners.SparkJobProvisioner.results',
            return_value={},
        ),
        'run': mocker.patch(
            'atmo.jobs.provisioners.SparkJobProvisioner.run',
            return_value='12345',
        ),
        'remove': mocker.patch(
            'atmo.jobs.provisioners.SparkJobProvisioner.remove',
            return_value=None,
        ),
    }


@pytest.fixture(autouse=True)
def patch_spark_emr_configuration(mocker):
    mocker.patch(
        'atmo.provisioners.Provisioner.spark_emr_configuration',
        return_value=[
            {
                'Classification': 'atmo-tests',
                'Properties': {
                    'passing': 'of-course',
                    'covering': 'everything',
                }
            },
        ]
    )


@pytest.fixture(autouse=True)
def patch_google_auth_discovery_endpoint(mocker):
    mocker.patch(
        'atmo.users.views.AtmoGoogleOAuth2Adapter.discovery_document',
        return_value={
            'authorization_endpoint': 'https://accounts.google.com/o/oauth2/v2/auth',
            'claims_supported': [
                'aud',
                'email',
                'email_verified',
                'exp',
                'family_name',
                'given_name',
                'iat',
                'iss',
                'locale',
                'name',
                'picture',
                'sub',
            ],
            'code_challenge_methods_supported': ['plain', 'S256'],
            'id_token_signing_alg_values_supported': ['RS256'],
            'issuer': 'https://accounts.google.com',
            'jwks_uri': 'https://www.googleapis.com/oauth2/v3/certs',
            'response_types_supported': [
                'code',
                'token',
                'id_token',
                'code token',
                'code id_token',
                'token id_token',
                'code token id_token',
                'none'
            ],
            'revocation_endpoint': 'https://accounts.google.com/o/oauth2/revoke',
            'scopes_supported': ['openid', 'email', 'profile'],
            'subject_types_supported': ['public'],
            'token_endpoint': 'https://www.googleapis.com/oauth2/v4/token',
            'token_endpoint_auth_methods_supported': [
                'client_secret_post',
                'client_secret_basic',
            ],
            'userinfo_endpoint': 'https://www.googleapis.com/oauth2/v3/userinfo',
        }
    )
