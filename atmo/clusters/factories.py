import factory

from . import models
from ..keys.factories import SSHKeyFactory
from ..users.factories import UserFactory


class ClusterFactory(factory.django.DjangoModelFactory):
    identifier = factory.Sequence(lambda n: 'test-cluster-%s' % n)
    size = 5
    ssh_key = factory.SubFactory(SSHKeyFactory)
    # start_date
    # end_date = None
    jobflow_id = factory.Sequence(lambda n: 'j-%s' % n)
    most_recent_status = ''
    master_address = ''
    expiration_mail_sent = False
    created_by = factory.SubFactory(UserFactory)
    emr_release = '5.3.0'

    class Meta:
        model = models.Cluster
