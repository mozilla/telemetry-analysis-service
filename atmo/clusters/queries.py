# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.db import models


class EMRReleaseQuerySet(models.QuerySet):

    def active(self):
        return self.filter(
            is_active=True,
        )

    def stable(self):
        return self.filter(
            is_experimental=False,
            is_deprecated=False,
            is_active=True,
        )

    def experimental(self):
        return self.filter(
            is_experimental=True,
            is_active=True,
        )

    def deprecated(self):
        return self.filter(
            is_deprecated=True,
            is_active=True,
        )


class ClusterQuerySet(models.QuerySet):

    def active(self):
        return self.filter(
            most_recent_status__in=self.model.ACTIVE_STATUS_LIST,
        )

    def terminated(self):
        return self.filter(
            most_recent_status__in=self.model.TERMINATED_STATUS_LIST,
        )

    def failed(self):
        return self.filter(
            most_recent_status__in=self.model.FAILED_STATUS_LIST,
        )
