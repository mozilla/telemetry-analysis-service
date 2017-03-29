import factory
from cryptography.hazmat.backends import \
    default_backend as crypto_default_backend
from cryptography.hazmat.primitives import \
    serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from . import models

from ..users.factories import UserFactory


def rsa_key():
    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=2048
    )
    return key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH
    ).decode('utf-8')


class SSHKeyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.SSHKey

    title = 'id_rsa'
    key = factory.LazyFunction(rsa_key)
    fingerprint = '50:a2:40:cb:2d:a2:38:64:66:ec:40:c7:a2:86:97:18'

    created_by = factory.SubFactory(UserFactory)
