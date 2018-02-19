# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from collections import namedtuple, OrderedDict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

from guardian.utils import get_user_obj_perms_model


class PermissionMigrator:
    """
    A custom django-guardian permission migration to be used when
    new model classes are added and users or groups require object
    permissions retroactively.
    """
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
        """
        The primary method to assign a permission to the user or group.
        """
        for params in self.params():
            self.object_permission.objects.get_or_create(**params)

    def remove(self):
        """
        The primary method to remove a permission to the user or group.
        """
        for params in self.params():
            self.object_permission.objects.filter(**params).delete()


class URLActionModel(models.Model):
    """
    A model base class to be used with URL patterns that define
    actions for models, e.g. /foo/bar/1/edit, /foo/bar/1/delete etc.
    """
    #: The list of actions to be used to reverse the URL patterns with
    url_actions = []
    #: The prefix to be used for the URL pattern names.
    url_prefix = None
    #: The delimiter to be used for the URL pattern names.
    url_delimiter = '-'
    #: The keyword argument name to be used in the URL pattern.
    url_kwarg_name = 'id'
    #: The field name to be used with the keyword argument in the URL pattern.
    url_field_name = 'id'

    @cached_property
    def url_tuple(self):
        return namedtuple('URLs', ' '.join(self.url_actions))

    @cached_property
    def urls(self):
        if self.url_prefix is None:
            raise ImproperlyConfigured(
                'Model %s is issing a correct url_prefix class attribute.' %
                self.__class__
            )
        if not self.url_actions:
            return ()
        values = OrderedDict()
        for name in self.url_actions:
            # e.g. poll-edit
            url_name = '%s%s%s' % (self.url_prefix, self.url_delimiter, name)
            field_value = getattr(self, self.url_field_name, None)
            values[name] = reverse(
                url_name,
                kwargs={
                    self.url_kwarg_name: field_value
                },
            )
        return self.url_tuple(**values)

    class Meta:
        abstract = True


class EditedAtModel(models.Model):
    """
    An abstract data model used by various other data models throughout
    ATMO that store timestamps for the creation and modification.
    """
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
    """
    An abstract data model that has a relation to the Django user model
    as configured by the ``AUTH_USER_MODEL`` setting. The reverse
    related name is ``created_<name of class>s``,
    e.g. ``user.created_clusters.all()`` where ``user`` is a ``User`` instance
    that has created various ``Cluster`` objects before.
    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_%(class)ss',  # e.g. user.created_clusters.all()
        help_text="User that created the instance."
    )

    class Meta:
        abstract = True

    def assign_permission(self, user, perm):
        """
        Assign permission to the given user, e.g. 'clusters.view_cluster',
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
