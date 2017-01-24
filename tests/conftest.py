import io
import uuid

import pytest
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from django.utils import timezone
from django.core.files.uploadedfile import InMemoryUploadedFile

from atmo.keys.models import SSHKey


@pytest.fixture
def now():
    return timezone.now()


@pytest.fixture
def test_user(client, django_user_model):
    test_user = django_user_model.objects.create_user(
        'testuser',
        'test@example.com',
        'testpassword',
    )
    client.force_login(test_user)
    return test_user


@pytest.fixture
def test_user2(client, django_user_model):
    test_user = django_user_model.objects.create_user(
        'testuser2',
        'test2@example.com',
        'testpassword2',
    )
    return test_user


@pytest.fixture
def notebook_maker():
    def maker(extension='ipynb'):
        return InMemoryUploadedFile(
            file=io.BytesIO('{}'),
            field_name='notebook',
            name='test-notebook.%s' % extension,
            content_type='text/plain',
            size=2,
            charset='utf8',
        )
    return maker


def make_ssh_key(test_user):
    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=2048
    )
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH
    )
    return SSHKey.objects.create(
        title=uuid.uuid4().hex,
        key=public_key,
        created_by=test_user,
    )


@pytest.fixture
def ssh_key(test_user):
    return make_ssh_key(test_user)


@pytest.fixture
def ssh_key_maker():
    return make_ssh_key
