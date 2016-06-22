import io
import mock
from datetime import datetime, timedelta
from pytz import UTC
from django.test import TestCase
from django.contrib.auth.models import User
from analysis_service.base import models


class TestAuthentication(TestCase):
    def setUp(self):
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')

    def test_that_login_page_is_csrf_protected(self):
        response = self.client.get('/login/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'csrfmiddlewaretoken', response.content)

    def test_that_login_works(self):
        self.assertTrue(self.client.login(username='john.smith', password='hunter2'))
        response = self.client.get('/login/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1], ('/', 302))


class TestCreateCluster(TestCase):
    @mock.patch('analysis_service.base.util.provisioning.cluster_start', return_value=u'12345')
    def setUp(self, cluster_start):
        self.start_date = datetime.now().replace(tzinfo=UTC)
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')
        self.client.force_login(self.test_user)

        # request that a new cluster be created
        self.response = self.client.post('/new-cluster/', {
            'identifier': 'test-cluster',
            'size': 5,
            'public_key': io.BytesIO('ssh-rsa AAAAB3'),
        }, follow=True)

        self.cluster_start = cluster_start

    def test_that_request_succeeded(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.redirect_chain[-1], ('/', 302))

    def test_that_cluster_is_correctly_provisioned(self):
        self.assertEqual(self.cluster_start.call_count, 1)
        (user_email, identifier, size, public_key) = self.cluster_start.call_args[0]
        self.assertEqual(user_email, 'john@smith.com')
        self.assertEqual(identifier, 'test-cluster')
        self.assertEqual(size, 5)
        self.assertEqual(public_key, 'ssh-rsa AAAAB3')

    def test_that_the_model_was_created_correctly(self):
        cluster = models.Cluster.objects.get(jobflow_id=u'12345')
        self.assertEqual(cluster.identifier, 'test-cluster')
        self.assertEqual(cluster.size, 5)
        self.assertEqual(cluster.public_key, 'ssh-rsa AAAAB3')
        self.assertTrue(
            self.start_date <= cluster.start_date <= self.start_date + timedelta(seconds=10)
        )
        self.assertEqual(cluster.created_by, self.test_user)
        self.assertTrue(User.objects.filter(username='john.smith').exists())


class TestEditCluster(TestCase):
    @mock.patch('analysis_service.base.util.provisioning.cluster_rename', return_value=None)
    def setUp(self, cluster_rename):
        self.start_date = datetime.now().replace(tzinfo=UTC)

        # create a test cluster to edit later
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')
        cluster = models.Cluster()
        cluster.identifier = 'test-cluster'
        cluster.size = 5
        cluster.public_key = 'ssh-rsa AAAAB3'
        cluster.created_by = self.test_user
        cluster.jobflow_id = u'12345'
        cluster.save()

        # request that the test cluster be edited
        self.client.force_login(self.test_user)
        self.response = self.client.post('/edit-cluster/', {
            'cluster': cluster.id,
            'identifier': 'new-cluster-name',
        }, follow=True)

        self.cluster_rename = cluster_rename

    def test_that_request_succeeded(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.redirect_chain[-1], ('/', 302))

    def test_that_cluster_is_correctly_edited(self):
        self.assertEqual(self.cluster_rename.call_count, 1)
        (jobflow_id, new_identifier) = self.cluster_rename.call_args[0]
        self.assertEqual(jobflow_id, u'12345')
        self.assertEqual(new_identifier, 'new-cluster-name')

    def test_that_the_model_was_edited_correctly(self):
        cluster = models.Cluster.objects.get(jobflow_id=u'12345')
        self.assertEqual(cluster.identifier, 'new-cluster-name')
        self.assertEqual(cluster.size, 5)
        self.assertEqual(cluster.public_key, 'ssh-rsa AAAAB3')
        self.assertTrue(
            self.start_date <= cluster.start_date <= self.start_date + timedelta(seconds=10)
        )
        self.assertEqual(cluster.created_by, self.test_user)


class TestDeleteCluster(TestCase):
    @mock.patch('analysis_service.base.util.provisioning.cluster_stop', return_value=None)
    def setUp(self, cluster_stop):
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')
        self.client.force_login(self.test_user)

        # create a test cluster to delete later
        cluster = models.Cluster()
        cluster.identifier = 'test-cluster'
        cluster.size = 5
        cluster.public_key = 'ssh-rsa AAAAB3'
        cluster.created_by = self.test_user
        cluster.jobflow_id = u'12345'
        cluster.save()

        # request that the test cluster be deleted
        self.response = self.client.post('/delete-cluster/', {
            'cluster': cluster.id,
        }, follow=True)

        self.cluster_stop = cluster_stop

    def test_that_request_succeeded(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.redirect_chain[-1], ('/', 302))

    def test_that_cluster_was_correctly_deleted(self):
        self.assertEqual(self.cluster_stop.call_count, 1)
        (jobflow_id,) = self.cluster_stop.call_args[0]
        self.assertEqual(jobflow_id, u'12345')

    def test_that_the_model_was_deleted_correctly(self):
        self.assertFalse(models.Cluster.objects.filter(jobflow_id=u'12345').exists())
        self.assertTrue(User.objects.filter(username='john.smith').exists())


class TestCreateScheduledSpark(TestCase):
    @mock.patch('analysis_service.base.util.scheduling.scheduled_spark_run', return_value=u'12345')
    def setUp(self, scheduled_spark_run):
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')
        self.client.force_login(self.test_user)

        # request that a new scheduled Spark job be created
        with mock.patch('analysis_service.base.util.scheduling.scheduled_spark_add') as mocked:
            def scheduled_spark_add(identifier, notebook_uploadedfile):
                self.saved_notebook_contents = notebook_uploadedfile.read()
                return u's3://test/test-notebook.ipynb'
            mocked.side_effect = scheduled_spark_add
            self.scheduled_spark_add = mocked

            self.response = self.client.post('/new-scheduled-spark/', {
                'identifier': 'test-scheduled-spark',
                'notebook': io.BytesIO('{}'),
                'result_visibility': 'private',
                'size': 5,
                'interval_in_hours': 24,
                'job_timeout': 12,
                'start_date': '2016-04-05 13:25:47',
            }, follow=True)

    def test_that_request_succeeded(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.redirect_chain[-1], ('/', 302))

    def test_that_the_notebook_was_uploaded_correctly(self):
        self.assertEqual(self.scheduled_spark_add.call_count, 1)
        (identifier, notebook_uploadedfile) = self.scheduled_spark_add.call_args[0]
        self.assertEqual(identifier, u'test-scheduled-spark')
        self.assertEqual(self.saved_notebook_contents, '{}')

    def test_that_the_model_was_created_correctly(self):
        scheduled_spark = models.ScheduledSpark.objects.get(identifier=u'test-scheduled-spark')
        self.assertEqual(scheduled_spark.identifier, 'test-scheduled-spark')
        self.assertEqual(scheduled_spark.notebook_s3_key, u's3://test/test-notebook.ipynb')
        self.assertEqual(scheduled_spark.result_visibility, 'private')
        self.assertEqual(scheduled_spark.size, 5)
        self.assertEqual(scheduled_spark.interval_in_hours, 24)
        self.assertEqual(scheduled_spark.job_timeout, 12)
        self.assertEqual(
            scheduled_spark.start_date,
            datetime(2016, 4, 5, 13, 25, 47).replace(tzinfo=UTC)
        )
        self.assertEqual(scheduled_spark.end_date, None)
        self.assertEqual(scheduled_spark.created_by, self.test_user)


class TestEditScheduledSpark(TestCase):
    @mock.patch('analysis_service.base.util.scheduling.scheduled_spark_run', return_value=u'12345')
    def setUp(self, scheduled_spark_run):
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')
        self.client.force_login(self.test_user)

        # create a test job to edit later
        scheduled_spark = models.ScheduledSpark()
        scheduled_spark.identifier = 'test-scheduled-spark'
        scheduled_spark.notebook_s3_key = u's3://test/test-notebook.ipynb'
        scheduled_spark.result_visibility = 'private'
        scheduled_spark.size = 5
        scheduled_spark.interval_in_hours = 24
        scheduled_spark.job_timeout = 12
        scheduled_spark.start_date = datetime(2016, 4, 5, 13, 25, 47).replace(tzinfo=UTC)
        scheduled_spark.created_by = self.test_user
        scheduled_spark.save()

        # request that a new scheduled Spark job be created
        self.response = self.client.post('/edit-scheduled-spark/', {
            'job': scheduled_spark.id,
            'identifier': 'new-scheduled-spark-name',
            'result_visibility': 'public',
            'size': 3,
            'interval_in_hours': 24 * 7,
            'job_timeout': 10,
            'start_date': '2016-03-08 11:17:35',
        }, follow=True)

    def test_that_request_succeeded(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.redirect_chain[-1], ('/', 302))

    def test_that_the_model_was_edited_correctly(self):
        scheduled_spark = models.ScheduledSpark.objects.get(identifier=u'new-scheduled-spark-name')
        self.assertEqual(scheduled_spark.identifier, 'new-scheduled-spark-name')
        self.assertEqual(scheduled_spark.notebook_s3_key, u's3://test/test-notebook.ipynb')
        self.assertEqual(scheduled_spark.result_visibility, 'public')
        self.assertEqual(scheduled_spark.size, 3)
        self.assertEqual(scheduled_spark.interval_in_hours, 24 * 7)
        self.assertEqual(scheduled_spark.job_timeout, 10)
        self.assertEqual(
            scheduled_spark.start_date,
            datetime(2016, 3, 8, 11, 17, 35).replace(tzinfo=UTC)
        )
        self.assertEqual(scheduled_spark.end_date, None)
        self.assertEqual(scheduled_spark.created_by, self.test_user)


class TestDeleteScheduledSpark(TestCase):
    @mock.patch('analysis_service.base.util.scheduling.scheduled_spark_remove', return_value=None)
    def setUp(self, scheduled_spark_remove):
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')
        self.client.force_login(self.test_user)

        # create a test job to delete later
        scheduled_spark = models.ScheduledSpark()
        scheduled_spark.identifier = 'test-scheduled-spark'
        scheduled_spark.notebook_s3_key = u's3://test/test-notebook.ipynb'
        scheduled_spark.result_visibility = 'private'
        scheduled_spark.size = 5
        scheduled_spark.interval_in_hours = 24
        scheduled_spark.job_timeout = 12
        scheduled_spark.start_date = datetime(2016, 4, 5, 13, 25, 47).replace(tzinfo=UTC)
        scheduled_spark.created_by = self.test_user
        scheduled_spark.save()

        # request that the test job be deleted
        self.response = self.client.post('/delete-scheduled-spark/', {
            'job': scheduled_spark.id,
        }, follow=True)

        self.scheduled_spark_remove = scheduled_spark_remove

    def test_that_request_succeeded(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.redirect_chain[-1], ('/', 302))

    def test_that_job_was_correctly_deleted(self):
        self.assertEqual(self.scheduled_spark_remove.call_count, 1)
        (notebook_s3_key,) = self.scheduled_spark_remove.call_args[0]
        self.assertEqual(notebook_s3_key, u's3://test/test-notebook.ipynb')

    def test_that_the_model_was_deleted_correctly(self):
        self.assertFalse(
            models.ScheduledSpark.objects.filter(identifier=u'test-scheduled-spark').exists()
        )
        self.assertTrue(User.objects.filter(username='john.smith').exists())
