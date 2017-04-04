# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

import pytest
from allauth.account.utils import user_display
from django.contrib.messages import get_messages
from django.core.urlresolvers import reverse
from django.utils import timezone

from atmo.clusters import models, tasks


@pytest.fixture
def cluster_provisioner_mocks(mocker):
    return {
        'start': mocker.patch(
            'atmo.clusters.provisioners.ClusterProvisioner.start',
            return_value='12345',
        ),
        'info': mocker.patch(
            'atmo.clusters.provisioners.ClusterProvisioner.info',
            return_value={
                'start_time': timezone.now(),
                'state': models.Cluster.STATUS_BOOTSTRAPPING,
                'state_change_reason_code': None,
                'state_change_reason_message': None,
                'public_dns': 'master.public.dns.name',
            },
        ),
        'stop': mocker.patch(
            'atmo.clusters.provisioners.ClusterProvisioner.stop',
            return_value=None,
        ),
    }


@pytest.mark.django_db
def test_cluster_form_defaults(client, user, ssh_key):
    response = client.post(reverse('clusters-new'), {}, follow=True)

    form = response.context['form']

    assert form.errors
    assert (form.initial['identifier'] ==
            '%s-telemetry-analysis' % user_display(user))
    assert form.initial['size'] == 1
    assert form.initial['lifetime'] == 8
    assert form.initial['ssh_key'] == ssh_key.id


@pytest.mark.django_db
def test_no_keys_redirect(client, user):
    response = client.post(reverse('clusters-new'), {}, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (reverse('keys-new'), 302)
    assert ('No SSH keys associated to you' in
            [m for m in get_messages(response.wsgi_request)][0].message)


@pytest.mark.django_db
def test_redirect_keys(client, user):
    assert not user.created_sshkeys.exists()
    response = client.get(reverse('clusters-new'), follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (reverse('keys-new'), 302)


@pytest.mark.django_db
def test_create_cluster(client, user, emr_release, ssh_key, cluster_provisioner_mocks):
    start_date = timezone.now()

    # request that a new cluster be created
    response = client.post(
        reverse('clusters-new'), {
            'new-identifier': 'test-cluster',
            'new-size': 5,
            'new-lifetime': 2,
            'new-ssh_key': ssh_key.id,
            'new-emr_release': emr_release.version,
        }, follow=True)
    cluster = models.Cluster.objects.get(jobflow_id='12345')

    assert response.status_code == 200
    assert response.redirect_chain[-1] == (cluster.urls.detail, 302)

    cluster_provisioner_mocks['start'].assert_called_with(
        user_email='test@example.com',
        identifier='test-cluster',
        emr_release=emr_release.version,
        size=5,
        public_key=ssh_key.key,
    )

    assert cluster.identifier == 'test-cluster'
    assert cluster.size == 5
    assert cluster.lifetime == 2
    assert cluster.ssh_key == ssh_key
    assert cluster.master_address == 'master.public.dns.name'
    assert (
        start_date <= cluster.start_date <= start_date + timedelta(seconds=10)
    )
    assert cluster.created_by == user
    assert cluster.emr_release == emr_release
    assert (
        "<atmo.clusters.models.Cluster identifier='test-cluster' size=5 lifetime=2"
        in
        repr(cluster)
    )


@pytest.mark.django_db
def test_is_expiring_soon(cluster):
    assert not cluster.is_expiring_soon
    cluster.end_date = timezone.now() + timedelta(minutes=59)  # the cut-off is at 1 hour
    cluster.save()
    assert cluster.is_expiring_soon


@pytest.mark.django_db
def test_empty_public_dns(client, cluster_provisioner_mocks, emr_release, user, ssh_key):
    cluster_provisioner_mocks['info'].return_value = {
        'start_time': timezone.now(),
        'state': models.Cluster.STATUS_BOOTSTRAPPING,
        'public_dns': None,
    }
    new_url = reverse('clusters-new')

    response = client.get(new_url)
    assert response.status_code == 200
    assert 'form' in response.context

    new_data = {
        'new-size': 5,
        'new-lifetime': 8,
        'new-ssh_key': ssh_key.id,
        'new-emr_release': emr_release.version
    }

    response = client.post(new_url, new_data, follow=True)
    assert response.context['form'].errors

    new_data.update({
        'new-identifier': 'test-cluster',
    })
    response = client.post(new_url, new_data, follow=True)
    assert cluster_provisioner_mocks['start'].call_count == 1
    cluster = models.Cluster.objects.get(jobflow_id='12345')
    assert cluster_provisioner_mocks['info'].call_count == 1
    assert cluster.master_address == ''


@pytest.mark.django_db
def test_terminate_cluster(client, cluster_provisioner_mocks, cluster_factory,
                           user, user2, ssh_key, emr_release):

    # create a test cluster to delete later
    cluster = cluster_factory(
        most_recent_status=models.Cluster.STATUS_BOOTSTRAPPING,
        created_by=user,
        emr_release=emr_release,
    )
    terminate_url = reverse('clusters-terminate', kwargs={'id': cluster.id})

    response = client.get(terminate_url)
    assert response.status_code == 200
    assert 'cluster' in response.context

    # setting state to TERMINATED so we can test the redirect to the detail page
    cluster.most_recent_status = cluster.STATUS_TERMINATED
    cluster.save()
    response = client.get(terminate_url, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (cluster.urls.detail, 302)

    # resettting to bootstrapping
    cluster.most_recent_status = cluster.STATUS_BOOTSTRAPPING
    cluster.save()

    # login the second user so we can check the delete_cluster permission
    client.force_login(user2)
    response = client.get(terminate_url, follow=True)
    assert response.status_code == 403

    # force login the regular test user
    client.force_login(user)

    # request that the test cluster be terminated
    response = client.post(terminate_url, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (cluster.urls.detail, 302)

    # the cluster was stopped
    cluster_provisioner_mocks['stop'].assert_called_with(cluster.jobflow_id)
    # but still exists in the database
    assert models.Cluster.objects.filter(jobflow_id=cluster.jobflow_id).exists()


@pytest.mark.django_db
def test_extend_cluster(client, user, emr_release, ssh_key, cluster):
    original_end_date = cluster.end_date

    assert cluster.lifetime_extension_count == 0
    assert cluster.end_date is not None

    cluster.extend(hours=3)
    cluster.refresh_from_db()
    assert cluster.lifetime_extension_count == 1
    assert cluster.end_date > original_end_date
    extended_end_date = cluster.end_date

    # request that a new cluster be created
    response = client.post(
        reverse('clusters-extend', kwargs={'id': cluster.id}), {
            'extend-extension': '2',
        }, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1] == (cluster.urls.detail, 302)

    cluster.refresh_from_db()
    assert cluster.lifetime_extension_count == 2
    assert cluster.end_date > extended_end_date


@pytest.mark.django_db
def test_send_expiration_mails(client, mocker, cluster):
    cluster.end_date = timezone.now() + timedelta(minutes=59)  # 1 hours is the cut-off
    cluster.most_recent_status = cluster.STATUS_WAITING
    cluster.save()
    mocked_send_email = mocker.patch('atmo.email.send_email')

    tasks.send_expiration_mails()

    mocked_send_email.assert_called_once_with(
        to=cluster.created_by.email,
        subject='[ATMO] Cluster %s is expiring soon!' % cluster.identifier,
        body=mocker.ANY,
    )
    cluster.refresh_from_db()
    assert cluster.expiration_mail_sent
