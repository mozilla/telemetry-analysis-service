# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.db import models
from django.utils import timezone

from ..clusters.models import Cluster


class SparkJobQuerySet(models.QuerySet):

    def with_runs(self):
        """
        The Spark jobs with runs.
        """
        return self.filter(runs__isnull=False)

    def active(self):
        """
        The Spark jobs that have an active cluster status.
        """
        return self.filter(
            runs__status__in=Cluster.ACTIVE_STATUS_LIST,
        )

    def terminated(self):
        """
        The Spark jobs that have a terminated cluster status.
        """
        return self.filter(
            runs__status__in=Cluster.TERMINATED_STATUS_LIST,
        )

    def failed(self):
        """
        The Spark jobs that have a failed cluster status.
        """
        return self.filter(
            runs__status__in=Cluster.FAILED_STATUS_LIST,
        )

    def lapsed(self):
        """
        The Spark jobs that have passed their end dates
        but haven't been expired yet.
        """
        return self.filter(
            end_date__lte=timezone.now(),
            expired_date__isnull=True,
        )


class SparkJobRunQuerySet(models.QuerySet):

    def active(self):
        """
        The Spark jobs that have an active cluster status.
        """
        return self.filter(status__in=Cluster.ACTIVE_STATUS_LIST)
