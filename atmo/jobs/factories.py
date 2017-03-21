import factory
from django.utils import timezone

from . import models

from ..clusters.factories import EMRReleaseFactory
from ..users.factories import UserFactory


class SparkJobFactory(factory.django.DjangoModelFactory):
    identifier = factory.Sequence(lambda n: 'test-spark-job-%s' % n)
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
    jobflow_id = '12345'
    status = ''
    scheduled_date = factory.LazyFunction(timezone.now)
    run_date = None
    terminated_date = None
    emr_release_version = factory.LazyAttribute(lambda run: run.spark_job.emr_release.version)

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
