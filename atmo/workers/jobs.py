# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.utils import timezone
from atmo.workers.models import Worker


def delete_workers():
    now = timezone.now()

    for worker in Worker.objects.filter(end_date__gte=now):
        # the worker is expired
        worker.delete()
