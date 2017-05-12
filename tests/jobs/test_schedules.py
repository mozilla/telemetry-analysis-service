# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

from redbeat.schedulers import RedBeatSchedulerEntry

from atmo.jobs.schedules import SparkJobSchedule


def test_init(spark_job):
    assert isinstance(spark_job.schedule, SparkJobSchedule)
    assert spark_job.schedule.spark_job == spark_job
    assert isinstance(spark_job.schedule.run_every, timedelta)
    assert (
        spark_job.schedule.name ==
        'atmo.jobs.tasks.run_job:%s' % spark_job.pk
    )


def test_added_on_save(spark_job_factory, user, emr_release):
    spark_job = spark_job_factory.build(
        created_by=user,
        emr_release=emr_release,
    )
    assert spark_job.schedule.get() is None
    spark_job.save()
    assert isinstance(spark_job.schedule.get(), RedBeatSchedulerEntry)


def test_get(spark_job):
    assert isinstance(spark_job.schedule.get(), RedBeatSchedulerEntry)
    assert repr(spark_job.schedule.get()) == repr(spark_job.schedule.create())


def test_add(mocker, spark_job):
    # entry exists due to save() call
    spark_job.schedule.delete()
    assert spark_job.schedule.get() is None
    mocker.spy(SparkJobSchedule, 'create')
    returned_entry = spark_job.schedule.add()
    assert spark_job.schedule.create.call_count == 1
    fetched_entry = spark_job.schedule.get()
    assert isinstance(fetched_entry, RedBeatSchedulerEntry)
    assert repr(returned_entry) == repr(fetched_entry)


def test_delete(spark_job):
    # entry exists due to save() call
    deleted = spark_job.schedule.delete()
    assert deleted
    deleted = spark_job.schedule.delete()
    assert not deleted
    assert spark_job.schedule.get() is None
