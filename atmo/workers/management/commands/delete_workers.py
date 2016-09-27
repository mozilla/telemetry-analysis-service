# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.core.management.base import BaseCommand
from atmo.workers.jobs import delete_workers


class Command(BaseCommand):
    help = 'Delete expired workers'

    def handle(self, *args, **options):
        delete_workers()
