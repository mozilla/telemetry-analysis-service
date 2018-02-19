# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.db import models


class EMRReleaseQuerySet(models.QuerySet):
    """
    A Django queryset for the :class:`~atmo.clusters.models.EMRRelease` model.
    """
    def natural_sort_by_version(self):
        """
        Sorts this queryset by the EMR version naturally (human-readable).
        """
        return self.extra(
            select={
                'natural_version': "string_to_array(version, '.')::int[]",
            },
        ).order_by('-natural_version')

    def active(self):
        return self.filter(
            is_active=True,
        )

    def stable(self):
        """
        The EMR releases that are considered stable.
        """
        return self.filter(
            is_experimental=False,
            is_deprecated=False,
            is_active=True,
        )

    def experimental(self):
        """
        The EMR releases that are considered experimental.
        """
        return self.filter(
            is_experimental=True,
            is_active=True,
        )

    def deprecated(self):
        """
        The EMR releases that are deprecated.
        """
        return self.filter(
            is_deprecated=True,
            is_active=True,
        )


class ClusterQuerySet(models.QuerySet):
    """A Django queryset that filters by cluster status.

    Used by the :class:`~atmo.clusters.models.Cluster` model.
    """

    def active(self):
        """
        The clusters that have an active status.
        """
        return self.filter(
            most_recent_status__in=self.model.ACTIVE_STATUS_LIST,
        )

    def terminated(self):
        """
        The clusters that have an terminated status.
        """
        return self.filter(
            most_recent_status__in=self.model.TERMINATED_STATUS_LIST,
        )

    def failed(self):
        """
        The clusters that have an failed status.
        """
        return self.filter(
            most_recent_status__in=self.model.FAILED_STATUS_LIST,
        )
