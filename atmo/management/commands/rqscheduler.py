# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import os

from django_rq import get_scheduler
from django_rq.management.commands.rqscheduler import Command as OriginalCommand


# django-rq doesn't support rqscheduler `retry` mode yet
# so we need to use the original startup script

class Command(OriginalCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('-b', '--burst', action='store_true', default=False,
                            help='Run in burst mode (quit after all work is done)')
        parser.add_argument('--retry', action='store_true', default=False,
                            help='Tell the scheduler to retry the registration process.')

    def handle(self, *args, **options):
        pid = options.get('pid')
        if pid:
            with open(os.path.expanduser(pid), "w") as fp:
                fp.write(str(os.getpid()))

        scheduler = get_scheduler(
            name=options.get('queue'), interval=options.get('interval'))
        scheduler.run(burst=options['burst'], retry=options['retry'])
