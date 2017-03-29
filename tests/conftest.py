import io

import pytest
from pytest_factoryboy import register as factory_register
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone

from atmo.clusters.factories import ClusterFactory
from atmo.clusters.provisioners import ClusterProvisioner
from atmo.jobs.factories import SparkJobFactory, SparkJobRunFactory, SparkJobWithRunFactory
from atmo.jobs.provisioners import SparkJobProvisioner

from atmo.keys.factories import SSHKeyFactory

from atmo.users.factories import UserFactory, GroupFactory


pytest_plugins = ['blockade']

factory_register(ClusterFactory)
factory_register(SparkJobFactory)
factory_register(SparkJobRunFactory)
factory_register(SparkJobWithRunFactory, 'spark_job_with_run')
factory_register(SSHKeyFactory)
factory_register(UserFactory)
factory_register(UserFactory, 'user2')
factory_register(GroupFactory)


@pytest.fixture
def now():
    return timezone.now()


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
def spark_job_provisioner():
    return SparkJobProvisioner()


@pytest.fixture
def cluster_provisioner():
    return ClusterProvisioner()


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
