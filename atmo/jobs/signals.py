# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.contrib.auth.models import Group

from guardian.shortcuts import assign_perm, remove_perm


def assign_group_perm(sender, instance, created, **kwargs):
    if created:
        group, _ = Group.objects.get_or_create(name='Spark job maintainers')
        assign_perm('jobs.view_sparkjob', group, instance)


def remove_group_perm(sender, instance, **kwargs):
    group, _ = Group.objects.get_or_create(name='Spark job maintainers')
    remove_perm('jobs.view_sparkjob', group, instance)
