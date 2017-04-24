# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from atmo.jobs.admin import run_now
from atmo.jobs.models import SparkJob


def test_run_now_action(mocker, spark_job_factory):
    run = mocker.patch('atmo.jobs.models.SparkJob.run')
    spark_job_factory.create_batch(5)
    run_now(None, None, SparkJob.objects.all())
    assert run.call_count == 5
