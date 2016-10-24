from django.db import models
from django.conf import settings


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
