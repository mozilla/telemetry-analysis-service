from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm, remove_perm


def assign_group_perm(sender, instance, created, **kwargs):
    if created:
        group, _ = Group.objects.get_or_create(name='Spark job maintainers')
        assign_perm('jobs.view_sparkjob', group, instance)


def remove_group_perm(sender, instance, **kwargs):
    group, _ = Group.objects.get_or_create(name='Spark job maintainers')
    remove_perm('jobs.view_sparkjob', group, instance)
