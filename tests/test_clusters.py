# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import io
from datetime import timedelta
from django.utils import timezone
from django.core.urlresolvers import reverse

from atmo.clusters import models


def test_create_cluster(mocker, monkeypatch, client, test_user):
    cluster_start = mocker.patch(
        'atmo.provisioning.cluster_start',
        return_value=u'12345',
    )
    mocker.patch(
        'atmo.provisioning.cluster_info',
        return_value={
            'start_time': timezone.now(),
            'state': models.Cluster.STATUS_BOOTSTRAPPING,
            'public_dns': 'master.public.dns.name',
        },
    )
    start_date = timezone.now()

    # request that a new cluster be created
    response = client.post(
        reverse('clusters-new'), {
            'new-identifier': 'test-cluster',
            'new-size': 5,
            'new-public_key': io.BytesIO('ssh-rsa AAAAB3'),
            'new-emr_release': models.Cluster.EMR_RELEASES_CHOICES_DEFAULT,
        }, follow=True)
    cluster = models.Cluster.objects.get(jobflow_id=u'12345')

    assert response.status_code == 200
    assert (response.redirect_chain[-1] ==
            (cluster.get_absolute_url(), 302))

    assert cluster_start.call_count == 1
    user_email, identifier, size, public_key, emr_release = \
        cluster_start.call_args[0]
    assert user_email == 'test@example.com'
    assert identifier == 'test-cluster'
    assert size == 5
    assert public_key == 'ssh-rsa AAAAB3'
    assert emr_release == models.Cluster.EMR_RELEASES_CHOICES_DEFAULT

    assert cluster.identifier == 'test-cluster'
    assert cluster.size == 5
    assert cluster.public_key == 'ssh-rsa AAAAB3'
    assert cluster.master_address == 'master.public.dns.name'
    assert (
        start_date <= cluster.start_date <= start_date + timedelta(seconds=10)
    )
    assert cluster.created_by == test_user
    assert cluster.emr_release == models.Cluster.EMR_RELEASES_CHOICES_DEFAULT


def test_empty_public_dns(mocker, monkeypatch, client, test_user):
    cluster_start = mocker.patch(
        'atmo.provisioning.cluster_start',
        return_value=u'67890',
    )
    cluster_info = mocker.patch(
        'atmo.provisioning.cluster_info',
        return_value={
            'start_time': timezone.now(),
            'state': models.Cluster.STATUS_BOOTSTRAPPING,
            'public_dns': None,
        },
    )
    new_url = reverse('clusters-new')

    response = client.get(new_url)
    assert response.status_code == 200
    assert 'form' in response.context

    new_data = {
        'new-size': 5,
        'new-public_key': io.BytesIO('ssh-rsa AAAAB3'),
        'new-emr_release': models.Cluster.EMR_RELEASES_CHOICES_DEFAULT
    }

    response = client.post(new_url, new_data, follow=True)
    assert response.context['form'].errors

    new_data.update({
        'new-identifier': 'test-cluster',
        'new-public_key': io.BytesIO('ssh-rsa AAAAB3'),
    })
    response = client.post(new_url, new_data, follow=True)
    assert cluster_start.call_count == 1
    cluster = models.Cluster.objects.get(jobflow_id=u'67890')
    assert cluster_info.call_count == 1
    assert cluster.master_address == ''


def test_terminate_cluster(mocker, monkeypatch, client, test_user):
    cluster_stop = mocker.patch(
        'atmo.provisioning.cluster_stop',
        return_value=None,
    )
    mocker.patch('atmo.provisioning.cluster_start', return_value=u'12345')
    mocker.patch(
        'atmo.provisioning.cluster_info',
        return_value={
            'start_time': timezone.now(),
            'state': models.Cluster.STATUS_BOOTSTRAPPING,
            'public_dns': 'master.public.dns.name',
        },
    )

    # create a test cluster to delete later
    cluster = models.Cluster.objects.create(
        identifier='test-cluster',
        size=5,
        public_key='ssh-rsa AAAAB3',
        created_by=test_user,
        jobflow_id=u'12345',
        most_recent_status=models.Cluster.STATUS_BOOTSTRAPPING,
    )
    assert repr(cluster) == '<Cluster test-cluster of size 5>'

    terminate_url = reverse('clusters-terminate', kwargs={'id': cluster.id})

    response = client.get(terminate_url)
    assert response.status_code == 200
    assert 'form' in response.context

    # setting state to TERMINATED so we can test the redirect to the detail page
    cluster.most_recent_status = cluster.STATUS_TERMINATED
    cluster.save()
    response = client.get(terminate_url, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (cluster.get_absolute_url(), 302)

    # resettting to bootstrapping
    cluster.most_recent_status = cluster.STATUS_BOOTSTRAPPING
    cluster.save()

    # request that the test cluster be deleted, but with a wrong identifier
    response = client.post(terminate_url, {
        'terminate-cluster': cluster.id,
        'terminate-confirmation': 'definitely-not-the-correct-identifier',
    }, follow=True)

    assert models.Cluster.objects.filter(pk=cluster.pk).exists()  # not deleted
    assert cluster_stop.call_count == 0  # but also not stopped
    assert 'Entered cluster identifier' in response.content

    # request that the test cluster be deleted, with the correct identifier
    response = client.post(terminate_url, {
        'terminate-cluster': cluster.id,
        'terminate-confirmation': cluster.identifier,
    }, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1] == (cluster.get_absolute_url(), 302)

    assert cluster_stop.call_count == 1
    (jobflow_id,) = cluster_stop.call_args[0]
    assert jobflow_id == u'12345'
    assert models.Cluster.objects.filter(jobflow_id=u'12345').exists()
