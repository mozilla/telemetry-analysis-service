import io
import mock
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from . import models


class TestCreateCluster(TestCase):
    @mock.patch('atmo.utils.provisioning.cluster_start', return_value=u'12345')
    def setUp(self, cluster_start):
        self.start_date = timezone.now()
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')
        self.client.force_login(self.test_user)

        # request that a new cluster be created
        self.response = self.client.post(reverse('clusters-new'), {
            'identifier': 'test-cluster',
            'size': 5,
            'public_key': io.BytesIO('ssh-rsa AAAAB3'),
            'emr_release': models.EMR_RELEASES[-1]

        }, follow=True)

        self.cluster_start = cluster_start

    def test_that_request_succeeded(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.redirect_chain[-1], ('/', 302))

    def test_that_cluster_is_correctly_provisioned(self):
        self.assertEqual(self.cluster_start.call_count, 1)
        (user_email, identifier, size, public_key, emr_release) = self.cluster_start.call_args[0]
        self.assertEqual(user_email, 'john@smith.com')
        self.assertEqual(identifier, 'test-cluster')
        self.assertEqual(size, 5)
        self.assertEqual(public_key, 'ssh-rsa AAAAB3')
        self.assertEqual(emr_release, models.EMR_RELEASES[-1])

    def test_that_the_model_was_created_correctly(self):
        cluster = models.Cluster.objects.get(jobflow_id=u'12345')
        self.assertEqual(cluster.identifier, 'test-cluster')
        self.assertEqual(cluster.size, 5)
        self.assertEqual(cluster.public_key, 'ssh-rsa AAAAB3')
        self.assertTrue(
            self.start_date <= cluster.start_date <= self.start_date + timedelta(seconds=10)
        )
        self.assertEqual(cluster.created_by, self.test_user)
        self.assertEqual(cluster.emr_release, models.EMR_RELEASES[-1])
        self.assertTrue(User.objects.filter(username='john.smith').exists())


class TestEditCluster(TestCase):
    @mock.patch('atmo.utils.provisioning.cluster_start', return_value=u'12345')
    @mock.patch('atmo.utils.provisioning.cluster_rename', return_value=None)
    def setUp(self, cluster_rename, cluster_start):
        self.start_date = timezone.now()

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
        self.response = self.client.post(reverse('clusters-edit'), {
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
    @mock.patch('atmo.utils.provisioning.cluster_stop', return_value=None)
    @mock.patch('atmo.utils.provisioning.cluster_start', return_value=u'12345')
    @mock.patch('atmo.utils.provisioning.cluster_info', return_value={
        'start_time': timezone.now(),
        'state': 'BOOTSTRAPPING',
        'public_dns': 'master.public.dns.name',
    })
    def setUp(self, cluster_info, cluster_start, cluster_stop):
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
        self.response = self.client.post(reverse('clusters-delete'), {
            'cluster': cluster.id,
        }, follow=True)

        self.cluster_stop = cluster_stop
        self.cluster_info = cluster_info

    def test_that_request_succeeded(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertEqual(self.response.redirect_chain[-1], ('/', 302))

    def test_that_cluster_was_correctly_deleted(self):
        self.assertEqual(self.cluster_stop.call_count, 1)
        (jobflow_id,) = self.cluster_stop.call_args[0]
        self.assertEqual(jobflow_id, u'12345')

    def test_that_the_cluster_object_still_exists(self):
        self.assertTrue(models.Cluster.objects.filter(jobflow_id=u'12345').exists())
