# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.core.management.base import BaseCommand
from ...jobs import delete_clusters


class Command(BaseCommand):
    help = 'Go through expired clusters to deactivate or warn about ones that are expiring'

    def handle(self, *args, **options):
        self.stdout.write('Deleting expired clusters...', ending='')
        delete_clusters()
        self.stdout.write('done.')
