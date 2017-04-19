# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

from celery.schedules import schedule
from redbeat.schedulers import RedBeatSchedulerEntry

from ..celery import celery


class SparkJobSchedule:
    task = 'atmo.jobs.tasks.run_job'

    def __init__(self, spark_job):
        self.spark_job = spark_job
        self.name = '%s:%s' % (self.task, self.spark_job.pk)
        self.run_every = timedelta(hours=self.spark_job.interval_in_hours)

    def create(self):
        entry = RedBeatSchedulerEntry(
            name=self.name,
            task=self.task,
            schedule=schedule(
                run_every=self.run_every,
                app=celery,
            ),
            args=(self.spark_job.pk,),
            kwargs={},
            app=celery,
        )
        return entry

    def get(self):
        """
        Get the scheduler entry for the task
        """
        try:
            entry = self.create()
            return RedBeatSchedulerEntry.from_key(entry.key, app=celery)
        except KeyError:
            return None

    def add(self):
        """
        Create and save an entry to the scheduler
        """
        entry = self.create()
        entry.save()
        return entry

    def delete(self):
        """
        If found, delete the entry from the scheduler
        """
        entry = self.get()
        if entry is None:
            return False
        else:
            entry.delete()
            return True
