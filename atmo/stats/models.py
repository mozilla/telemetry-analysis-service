# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone


class Metric(models.Model):
    created_at = models.DateTimeField(
        editable=False,
        blank=True,
        default=timezone.now,
        db_index=True,
    )
    key = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Name of the metric being recorded',
    )
    value = models.PositiveIntegerField(
        help_text='Integer value of the metric',
    )
    data = JSONField(
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        help_text='Extra data about this metric',
    )

    @classmethod
    def record(cls, key, value=1, **kwargs):
        """
        Create a new entry in the ``Metric`` table.

        :param key:
            The metric key name.

        :param value:
            The metric value as an integer.

        :param data:
            Any extra data to be stored with this record as a dictionary.

        """
        created_at = kwargs.pop('created_at', None) or timezone.now()
        data = kwargs.pop('data', None)

        cls.objects.create(
            created_at=created_at,
            key=key,
            value=value,
            data=data
        )
