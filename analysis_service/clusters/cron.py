from datetime import datetime, timedelta

import kronos

from ..utils import email
from .models import Cluster


# this function is called every hour
@kronos.register('0 * * * *')
def delete_workers():
    now = datetime.now()

    # go through clusters to delete or warn about ones that are expiring
    for cluster in Cluster.objects.all():
        if cluster.end_date >= now:  # the cluster is expired
            cluster.delete()
        elif cluster.end_date >= now + timedelta(hours=1):  # the cluster will expire in an hour
            email.send_email(
                email_address = cluster.created_by.email,
                subject = "Cluster {} is expiring soon!".format(cluster.identifier),
                body = (
                    "Your cluster {} will be terminated in roughly one hour, around {}. "
                    "Please save all unsaved work before the machine is shut down.\n"
                    "\n"
                    "This is an automated message from the Telemetry Analysis service. "
                    "See https://analysis.telemetry.mozilla.org/ for more details."
                ).format(cluster.identifier, now + timedelta(hours=1))
            )
