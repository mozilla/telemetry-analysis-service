import factory

from django.utils import timezone

from . import models
from ..keys.factories import SSHKeyFactory
from ..users.factories import UserFactory


class EMRReleaseFactory(factory.django.DjangoModelFactory):
    version = '5.3.0'
    changelog_url = \
        'https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-5.3.0/emr-release-components.html'
    help_text = 'just a help text'
    is_experimental = False
    is_deprecated = False

    class Meta:
        model = models.EMRRelease


class ClusterFactory(factory.django.DjangoModelFactory):
    identifier = factory.Sequence(lambda n: 'test-cluster-%s' % n)
    size = 5
    lifetime = models.Cluster.DEFAULT_LIFETIME
    ssh_key = factory.SubFactory(SSHKeyFactory)
    start_date = factory.LazyFunction(timezone.now)
    end_date = None
    jobflow_id = factory.Sequence(lambda n: 'j-%s' % n)
    most_recent_status = ''
    master_address = ''
    expiration_mail_sent = False
    created_by = factory.SubFactory(UserFactory)
    emr_release = factory.SubFactory(EMRReleaseFactory)

    class Meta:
        model = models.Cluster
