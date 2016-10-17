# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.core.management.base import BaseCommand
from ...jobs import launch_jobs


class Command(BaseCommand):
    help = 'Launch scheduled jobs if necessary'

    def handle(self, *args, **options):
        self.stdout.write('Launching scheduled jobs...', ending='')
        launch_jobs()
        self.stdout.write('done.')
