# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import factory

from . import models
from .. import names
from ..keys.factories import SSHKeyFactory
from ..users.factories import UserFactory


class EMRReleaseFactory(factory.django.DjangoModelFactory):
    version = factory.Sequence(lambda n: '1.%s' % n)
    changelog_url = factory.LazyAttribute(
        lambda emr_release: (
            'https://docs.aws.amazon.com/emr/latest/ReleaseGuide/'
            'emr-%s/emr-release-components.html' % emr_release.version
        )
    )
    help_text = 'just a help text'
    is_active = True
    is_experimental = False
    is_deprecated = False

    class Meta:
        model = models.EMRRelease


class ClusterFactory(factory.django.DjangoModelFactory):
    identifier = factory.LazyFunction(names.random_scientist)
    size = 5
    lifetime = models.Cluster.DEFAULT_LIFETIME
    ssh_key = factory.SubFactory(SSHKeyFactory)
    jobflow_id = factory.Sequence(lambda n: 'j-%s' % n)
    most_recent_status = ''
    master_address = ''
    expiration_mail_sent = False
    created_by = factory.SubFactory(UserFactory)
    emr_release = factory.SubFactory(EMRReleaseFactory)

    class Meta:
        model = models.Cluster
