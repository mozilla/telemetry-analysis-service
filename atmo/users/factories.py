# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import factory

from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import make_password


class GroupFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "Group #%s" % n)

    class Meta:
        model = Group


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: 'user%s' % n)
    first_name = factory.Sequence(lambda n: "user %03d" % n)
    email = 'test@example.com'

    class Meta:
        model = User

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        return make_password('password')

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for group in extracted:
                self.groups.add(group)
