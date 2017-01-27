# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import newrelic.agent

from .models import SparkJob


@newrelic.agent.background_task(group='RQ')
def run_jobs():
    """
    Run all the scheduled tasks that are supposed to run.
    """
    run_jobs = []
    for job in SparkJob.objects.all():
        # first let's update the status to update most_recent_status
        job.update_status()
        job.save()

        # then let's check if the job should be run at all
        if job.should_run():
            job.run()
            run_jobs.append(job.identifier)

        # and then check if the job is expired and terminate it if needed
        if job.is_expired:
            # This shouldn't be required as we set a timeout in the bootstrap script,
            # but let's keep it as a guard.
            job.terminate()
    return run_jobs
