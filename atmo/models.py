from django.db import models
from django.conf import settings

from guardian.utils import get_user_obj_perms_model


class PermissionMigrator(object):

    def __init__(self, apps, model, user_field):
        self.codename = 'view_%s' % model._meta.model_name
        self.model = model
        self.user_field = user_field
        self.content_type = apps.get_model('contenttypes', 'ContentType').objects.get_for_model(model)
        Permission = apps.get_model('auth', 'Permission')
        self.perm, created = Permission.objects.get_or_create(
            content_type=self.content_type,
            codename=self.codename,
            defaults={'name': 'Can view %s' % model._meta.model_name}
        )
        self.user_object_permission = apps.get_model('guardian', 'UserObjectPermission')

    def params(self):
        objs = []
        for obj in self.model.objects.all():
            objs.append({
                'permission': self.perm,
                'content_type': self.content_type,
                'object_pk': obj.pk,
                'user': getattr(obj, self.user_field),
            })
        return objs

    def assign(self):
        for params in self.params():
            self.user_object_permission.objects.get_or_create(**params)

    def remove(self):
        for params in self.params():
            self.user_object_permission.objects.filter(**params).delete()


class CreatedByModel(models.Model):

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_%(class)ss',  # e.g. user.created_clusters.all()
        help_text="User that created the instance."
    )

    class Meta:
        abstract = True

    def assign_view_permission(self, user):
        """
        assign view permissions to the given user, e.g. 'clusters.view_cluster',
        """
        perm = 'view_%s' % self._meta.model_name
        get_user_obj_perms_model(self).objects.assign_perm(perm, user, self)

    def save(self, *args, **kwargs):
        instance = super(CreatedByModel, self).save(*args, **kwargs)
        self.assign_view_permission(self.created_by)
        return instance


class EMRReleaseModel(models.Model):
    EMR_RELEASES = settings.AWS_CONFIG['EMR_RELEASES']
    # Default release is the first item, order should be from latest to oldest
    EMR_RELEASES_CHOICES = list(zip(*(EMR_RELEASES,) * 2))
    EMR_RELEASES_CHOICES_DEFAULT = EMR_RELEASES[0]

    emr_release = models.CharField(
        max_length=50,
        verbose_name='EMR release version',
        choices=EMR_RELEASES_CHOICES,
        default=EMR_RELEASES_CHOICES_DEFAULT,
        help_text=('Different EMR versions have different versions '
                   'of software like Hadoop, Spark, etc'),
    )

    class Meta:
        abstract = True


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
