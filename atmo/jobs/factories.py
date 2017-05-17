# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import factory
from django.utils import timezone

from . import models
from .. import names
from ..clusters.factories import EMRReleaseFactory
from ..users.factories import UserFactory


class SparkJobFactory(factory.django.DjangoModelFactory):
    identifier = factory.LazyFunction(names.random_scientist)
    description = 'some description'
    notebook_s3_key = 'jobs/test-spark-job/test-notebook.ipynb'
    result_visibility = models.SparkJob.RESULT_PRIVATE
    size = 5
    interval_in_hours = models.SparkJob.INTERVAL_DAILY
    job_timeout = 12
    start_date = factory.LazyFunction(timezone.now)
    end_date = None
    is_enabled = True
    created_by = factory.SubFactory(UserFactory)
    emr_release = factory.SubFactory(EMRReleaseFactory)

    class Meta:
        model = models.SparkJob


class SparkJobRunFactory(factory.django.DjangoModelFactory):
    spark_job = factory.SubFactory(SparkJobFactory)
    jobflow_id = factory.Sequence(lambda n: 'j-%s' % n)
    status = models.DEFAULT_STATUS
    scheduled_date = factory.LazyFunction(timezone.now)
    run_date = None
    finished_at = None
    emr_release_version = factory.LazyAttribute(lambda run: run.spark_job.emr_release.version)
    created_at = factory.LazyFunction(timezone.now)

    class Meta:
        model = models.SparkJobRun


class SparkJobWithRunFactory(SparkJobFactory):
    """
    A SparkJob factory that automatically creates a SparkJobRun
    """
    notebook_s3_key = factory.LazyAttributeSequence(
        lambda job, n: 'jobs/%s/test-notebook-%s.ipynb' % (job.identifier, n)
    )
    run = factory.RelatedFactory(SparkJobRunFactory, 'spark_job')
