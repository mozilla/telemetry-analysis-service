import io
import mock
from datetime import datetime, timedelta
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from . import models


class TestCreateSparkJob(TestCase):
    @mock.patch('atmo.scheduling.spark_job_run', return_value=u'12345')
    @mock.patch('atmo.scheduling.spark_job_get', return_value=u'content')
    def setUp(self, spark_job_get, spark_job_run):
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')
        self.client.force_login(self.test_user)

        # request that a new scheduled Spark job be created
        with mock.patch('atmo.scheduling.spark_job_add') as mocked:
            def spark_job_add(identifier, notebook_uploadedfile):
                self.saved_notebook_contents = notebook_uploadedfile.read()
                return u's3://test/test-notebook.ipynb'
            mocked.side_effect = spark_job_add
            self.spark_job_add = mocked

            self.response = self.client.post(reverse('jobs-new'), {
                'new-identifier': 'test-spark-job',
                'new-notebook': io.BytesIO('{}'),
                'new-result_visibility': 'private',
                'new-size': 5,
                'new-interval_in_hours': 24,
                'new-job_timeout': 12,
                'new-start_date': '2016-04-05 13:25:47',
            }, follow=True)
        self.spark_job = models.SparkJob.objects.get(identifier='test-spark-job')

    def test_that_request_succeeded(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.redirect_chain[-1],
                         (self.spark_job.get_absolute_url(), 302))

    def test_that_the_notebook_was_uploaded_correctly(self):
        self.assertEqual(self.spark_job_add.call_count, 1)
        (identifier, notebook_uploadedfile) = self.spark_job_add.call_args[0]
        self.assertEqual(identifier, u'test-spark-job')
        self.assertEqual(self.saved_notebook_contents, '{}')

    def test_that_the_model_was_created_correctly(self):
        spark_job = models.SparkJob.objects.get(identifier=u'test-spark-job')
        self.assertEqual(spark_job.identifier, 'test-spark-job')
        self.assertEqual(spark_job.notebook_s3_key, u's3://test/test-notebook.ipynb')
        self.assertEqual(spark_job.result_visibility, 'private')
        self.assertEqual(spark_job.size, 5)
        self.assertEqual(spark_job.interval_in_hours, 24)
        self.assertEqual(spark_job.job_timeout, 12)
        self.assertEqual(
            spark_job.start_date,
            timezone.make_aware(datetime(2016, 4, 5, 13, 25, 47))
        )
        self.assertEqual(spark_job.end_date, None)
        self.assertEqual(spark_job.created_by, self.test_user)


class TestEditSparkJob(TestCase):
    @mock.patch('atmo.scheduling.spark_job_run', return_value=u'12345')
    @mock.patch('atmo.scheduling.spark_job_get', return_value=u'content')
    def setUp(self, spark_job_get, spark_job_run):
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')
        self.client.force_login(self.test_user)

        # create a test job to edit later
        spark_job = models.SparkJob()
        spark_job.identifier = 'test-spark-job'
        spark_job.notebook_s3_key = u's3://test/test-notebook.ipynb'
        spark_job.result_visibility = 'private'
        spark_job.size = 5
        spark_job.interval_in_hours = 24
        spark_job.job_timeout = 12
        spark_job.start_date = timezone.make_aware(datetime(2016, 4, 5, 13, 25, 47))
        spark_job.created_by = self.test_user
        spark_job.save()

        # request that a new scheduled Spark job be created
        self.response = self.client.post(
            reverse('jobs-edit', kwargs={
                'id': spark_job.id,
            }), {
                'edit-job': spark_job.id,
                'edit-identifier': 'new-spark-job-name',
                'edit-result_visibility': 'public',
                'edit-size': 3,
                'edit-interval_in_hours': 24 * 7,
                'edit-job_timeout': 10,
                'edit-start_date': '2016-03-08 11:17:35',
            }, follow=True)
        self.spark_job = spark_job

    def test_that_request_succeeded(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.redirect_chain[-1],
                         (self.spark_job.get_absolute_url(), 302))

    def test_that_the_model_was_edited_correctly(self):
        spark_job = models.SparkJob.objects.get(identifier=u'new-spark-job-name')
        self.assertEqual(spark_job.identifier, 'new-spark-job-name')
        self.assertEqual(spark_job.notebook_s3_key, u's3://test/test-notebook.ipynb')
        self.assertEqual(spark_job.result_visibility, 'public')
        self.assertEqual(spark_job.size, 3)
        self.assertEqual(spark_job.interval_in_hours, 24 * 7)
        self.assertEqual(spark_job.job_timeout, 10)
        self.assertEqual(
            spark_job.start_date,
            timezone.make_aware(datetime(2016, 3, 8, 11, 17, 35))
        )
        self.assertEqual(spark_job.end_date, None)
        self.assertEqual(spark_job.created_by, self.test_user)


class TestDeleteSparkJob(TestCase):
    @mock.patch('atmo.scheduling.spark_job_remove', return_value=None)
    @mock.patch('atmo.scheduling.spark_job_get', return_value=u'content')
    def setUp(self, spark_job_get, spark_job_remove):
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')
        self.client.force_login(self.test_user)

        # create a test job to delete later
        spark_job = models.SparkJob()
        spark_job.identifier = 'test-spark-job'
        spark_job.notebook_s3_key = u's3://test/test-notebook.ipynb'
        spark_job.result_visibility = 'private'
        spark_job.size = 5
        spark_job.interval_in_hours = 24
        spark_job.job_timeout = 12
        spark_job.start_date = timezone.make_aware(datetime(2016, 4, 5, 13, 25, 47))
        spark_job.created_by = self.test_user
        spark_job.save()

        # request that the test job be deleted
        self.response = self.client.post(
            reverse('jobs-delete', kwargs={
                'id': spark_job.id,
            }), {
                'delete-job': spark_job.id,
                'delete-confirmation': spark_job.identifier,
            }, follow=True)

        self.spark_job_remove = spark_job_remove

    def test_that_request_succeeded(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.redirect_chain[-1], ('/', 302))

    def test_that_job_was_correctly_deleted(self):
        self.assertEqual(self.spark_job_remove.call_count, 1)
        (notebook_s3_key,) = self.spark_job_remove.call_args[0]
        self.assertEqual(notebook_s3_key, u's3://test/test-notebook.ipynb')

    def test_that_the_model_was_deleted_correctly(self):
        self.assertFalse(
            models.SparkJob.objects.filter(identifier=u'test-spark-job').exists()
        )
        self.assertTrue(User.objects.filter(username='john.smith').exists())


class TestSparkJobShouldRun(TestCase):

    def setUp(self):
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')
        now = timezone.now()
        self.spark_job_first_run = models.SparkJob.objects.create(
            identifier='test-spark-job',
            notebook_s3_key=u's3://test/test-notebook.ipynb',
            result_visibility='private',
            size=5,
            interval_in_hours=24,
            job_timeout=12,
            start_date=now - timedelta(hours=1),
            created_by=self.test_user,
        )

        self.spark_job_not_active = models.SparkJob.objects.create(
            identifier='test-spark-job',
            notebook_s3_key=u's3://test/test-notebook.ipynb',
            result_visibility='private',
            size=5,
            interval_in_hours=24,
            job_timeout=12,
            start_date=now + timedelta(hours=1),
            created_by=self.test_user
        )

        self.spark_job_expired = models.SparkJob.objects.create(
            identifier='test-spark-job',
            notebook_s3_key=u's3://test/test-notebook.ipynb',
            result_visibility='private',
            size=5,
            interval_in_hours=24,
            job_timeout=12,
            start_date=now - timedelta(hours=1),
            end_date=now,
            created_by=self.test_user,
        )

        self.spark_job_not_ready = models.SparkJob.objects.create(
            identifier='test-spark-job',
            notebook_s3_key=u's3://test/test-notebook.ipynb',
            result_visibility='private',
            size=5,
            interval_in_hours=24,
            job_timeout=12,
            start_date=now - timedelta(hours=2),
            last_run_date=now - timedelta(hours=1),
            created_by=self.test_user,
        )

        self.spark_job_second_run = models.SparkJob.objects.create(
            identifier='test-spark-job',
            notebook_s3_key=u's3://test/test-notebook.ipynb',
            result_visibility='private',
            size=5,
            interval_in_hours=1,
            job_timeout=12,
            start_date=now - timedelta(days=1),
            last_run_date=now - timedelta(hours=2),
            created_by=self.test_user,
        )
        self.now = now

    def test_spark_job_first_run(self):
        self.assertTrue(self.spark_job_first_run.should_run(at_time=self.now))

    def test_spark_job_not_active(self):
        self.assertFalse(self.spark_job_not_active.should_run(at_time=self.now))

    def test_spark_job_expired(self):
        self.assertFalse(self.spark_job_expired.should_run(at_time=self.now + timedelta(seconds=1)))

    def test_spark_job_not_ready(self):
        self.assertFalse(self.spark_job_not_ready.should_run(at_time=self.now))

    def test_spark_job_second_run(self):
        self.assertTrue(self.spark_job_second_run.should_run(at_time=self.now))
