# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf import settings
from django.db import models
from django.utils import timezone

from guardian.utils import get_user_obj_perms_model


class PermissionMigrator:

    def __init__(self, apps, model, perm, user_field=None, group=None):
        self.codename = '%s_%s' % (perm, model._meta.model_name)
        self.model = model
        self.user_field = user_field
        self.group = group
        ContentType = apps.get_model('contenttypes', 'ContentType')
        self.content_type = ContentType.objects.get_for_model(model)
        Permission = apps.get_model('auth', 'Permission')
        self.perm, created = Permission.objects.get_or_create(
            content_type=self.content_type,
            codename=self.codename,
            defaults={'name': 'Can %s %s' % (perm, model._meta.model_name)}
        )

        if self.user_field:
            self.object_permission = apps.get_model('guardian',
                                                    'UserObjectPermission')
        elif self.group:
            self.object_permission = apps.get_model('guardian',
                                                    'GroupObjectPermission')

    def params(self):
        objs = []
        for obj in self.model.objects.all():
            kwargs = {
                'permission': self.perm,
                'content_type': self.content_type,
                'object_pk': obj.pk,
            }
            if self.user_field:
                kwargs['user'] = getattr(obj, self.user_field)
            elif self.group:
                kwargs['group'] = self.group
            objs.append(kwargs)
        return objs

    def assign(self):
        for params in self.params():
            self.object_permission.objects.get_or_create(**params)

    def remove(self):
        for params in self.params():
            self.object_permission.objects.filter(**params).delete()


class EditedAtModel(models.Model):

    created_at = models.DateTimeField(
        editable=False,
        blank=True,
        default=timezone.now,
    )
    modified_at = models.DateTimeField(
        editable=False,
        blank=True,
        default=timezone.now,
    )

    class Meta:
        abstract = True
        get_latest_by = 'modified_at'
        ordering = ('-modified_at', '-created_at',)

    def save(self, *args, **kwargs):
        self.modified_at = timezone.now()
        super().save(*args, **kwargs)


class CreatedByModel(models.Model):

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_%(class)ss',  # e.g. user.created_clusters.all()
        help_text="User that created the instance."
    )

    class Meta:
        abstract = True

    def assign_permission(self, user, perm):
        """
        assign permission to the given user, e.g. 'clusters.view_cluster',
        """
        perm = '%s_%s' % (perm, self._meta.model_name)
        get_user_obj_perms_model(self).objects.assign_perm(perm, user, self)

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        # note: no "add" permission, because it's useless for objects
        for perm in ['change', 'delete', 'view']:
            self.assign_permission(self.created_by, perm)
        return instance


def next_field_value(model_cls, field_name, field_value,
                     start=2, separator='-', max_length=0, queryset=None):
    """
    For the given model class, field name and field value provide
    a "next" value, which basically means a counter appended to the value.
    """
    if queryset is None:
        queryset = model_cls._default_manager.all()

    field_max_length = model_cls._meta.get_field(field_name).max_length
    if not max_length or max_length > field_max_length:
        max_length = field_max_length

    try:
        split_value = field_value.split(separator)
        int(split_value[-1])
        original = separator.join(split_value[:-1])
    except ValueError:
        original = field_value

    counter = start
    while not field_value or queryset.filter(**{field_name: field_value}):
        field_value = original
        end = '-%s' % counter
        if max_length and len(field_value) + len(end) > max_length:
            field_value = field_value[:max_length - len(end)]
        field_value = '%s%s' % (field_value, end)
        counter += 1

    return field_value
