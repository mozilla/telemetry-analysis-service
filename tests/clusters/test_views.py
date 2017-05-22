# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

import pytest
from django.core.urlresolvers import reverse
from django.db import transaction
from django.utils import timezone

from atmo import names
from atmo.clusters import models


def test_form_defaults(client, user, ssh_key):
    response = client.post(reverse('clusters-new'), {}, follow=True)

    form = response.context['form']

    assert form.errors
    adjective, noun, suffix = form.initial['identifier'].split('-')
    assert adjective in names.adjectives
    assert noun in names.scientists
    assert len(suffix) == 4
    assert form.initial['size'] == 1
    assert form.initial['lifetime'] == 8
    assert form.initial['ssh_key'] == ssh_key


def test_multiple_ssh_keys(client, user, ssh_key, ssh_key_factory):
    ssh_key2 = ssh_key_factory(created_by=user)
    assert user.created_sshkeys.count() == 2
    response = client.get(reverse('clusters-new'), {}, follow=True)
    assert response.context['form'].initial['ssh_key'] == ssh_key2


def test_ssh_key_radioset(client, user, ssh_key, ssh_key_factory):
    ssh_key_factory.create_batch(5, created_by=user)
    assert user.created_sshkeys.count() == 6
    response = client.get(reverse('clusters-new'), {}, follow=True)
    assert (
        response.context['form']['ssh_key'].field.widget.attrs.get('class') ==
        'radioset'
    )
    # a seventh key unlocks the secret radiobutton
    ssh_key_factory(created_by=user)
    response = client.get(reverse('clusters-new'), {}, follow=True)
    assert (
        response.context['form']['ssh_key'].field.widget.attrs.get('class') !=
        'radioset'
    )


def test_no_keys_redirect(client, messages, user):
    response = client.post(reverse('clusters-new'), {}, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (reverse('keys-new'), 302)
    messages.assert_message_contains(response, 'No SSH keys associated to you')


def test_redirect_keys(client, user):
    assert not user.created_sshkeys.exists()
    response = client.get(reverse('clusters-new'), follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (reverse('keys-new'), 302)


@pytest.mark.usefixtures('transactional_db')
def test_create(client, user, emr_release, ssh_key, cluster_provisioner_mocks):
    created_at = timezone.now()

    with transaction.atomic():
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
        user_username=user.username,
        user_email=user.email,
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
        created_at <= cluster.created_at <= created_at + timedelta(seconds=10)
    )
    assert cluster.created_by == user
    assert cluster.emr_release == emr_release


@pytest.mark.usefixtures('transactional_db')
def test_empty_public_dns(client, cluster_provisioner_mocks, mocker, emr_release, user, ssh_key):
    sync = mocker.spy(models.Cluster, 'sync')

    cluster_provisioner_mocks['info'].return_value = {
        'creation_datetime': timezone.now(),
        'ready_datetime': None,
        'end_datetime': None,
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

    with transaction.atomic():
        response = client.post(new_url, new_data, follow=True)
        assert response.context['form'].errors

    new_data.update({
        'new-identifier': 'test-cluster',
    })

    with transaction.atomic():
        response = client.post(new_url, new_data, follow=True)

    cluster = models.Cluster.objects.get(jobflow_id='12345')
    assert sync.call_count == 1
    assert cluster_provisioner_mocks['start'].call_count == 1
    assert cluster_provisioner_mocks['info'].call_count == 1
    assert cluster.master_address == ''


def test_terminate(client, cluster_provisioner_mocks, cluster_factory,
                   user, user2, ssh_key, emr_release):

    # create a test cluster to delete later
    cluster = cluster_factory(
        most_recent_status=models.Cluster.STATUS_BOOTSTRAPPING,
        created_by=user,
        emr_release=emr_release,
    )
    response = client.get(cluster.urls.terminate)
    assert response.status_code == 200
    assert 'cluster' in response.context

    # setting state to TERMINATED so we can test the redirect to the detail page
    cluster.most_recent_status = cluster.STATUS_TERMINATED
    cluster.save()
    response = client.get(cluster.urls.terminate, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (cluster.urls.detail, 302)

    # resettting to bootstrapping
    cluster.most_recent_status = cluster.STATUS_BOOTSTRAPPING
    cluster.save()

    # login the second user so we can check the delete_cluster permission
    client.force_login(user2)
    response = client.get(cluster.urls.terminate, follow=True)
    assert response.status_code == 403

    # force login the regular test user
    client.force_login(user)

    # request that the test cluster be terminated
    response = client.post(cluster.urls.terminate, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (cluster.urls.detail, 302)

    # the cluster was stopped
    cluster_provisioner_mocks['stop'].assert_called_with(cluster.jobflow_id)
    # but still exists in the database
    assert models.Cluster.objects.filter(jobflow_id=cluster.jobflow_id).exists()


def test_extend_success(client, user, cluster_factory):
    cluster = cluster_factory(
        most_recent_status=models.Cluster.STATUS_WAITING,
        created_by=user,
    )
    original_expires_at = cluster.expires_at

    # extend the cluster via the extend view
    response = client.get(cluster.urls.extend, follow=True)
    assert response.status_code == 200
    assert response.context['form'].initial == {
        'extension': models.Cluster.DEFAULT_LIFETIME,
    }

    # extend the cluster via the extend view
    response = client.post(cluster.urls.extend, {
        'lalala': '2',
    }, follow=True)
    assert response.status_code == 200
    assert response.context['form'].errors
    assert not response.context['form'].is_valid()

    # extend the cluster via the extend view
    response = client.post(cluster.urls.extend, {
        'extend-extension': '2',
    }, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1] == (cluster.urls.detail, 302)

    cluster.refresh_from_db()
    assert cluster.lifetime_extension_count == 1
    assert cluster.expires_at > original_expires_at


def test_extend_error(client, messages, user, cluster_factory):
    cluster = cluster_factory(
        most_recent_status=models.Cluster.STATUS_TERMINATED,
        created_by=user,
    )
    original_expires_at = cluster.expires_at

    # extend the cluster via the extend view
    response = client.post(cluster.urls.extend, {
        'extend-extension': '2'
    }, follow=True)

    assert response.status_code == 200
    assert response.redirect_chain[-1] == (cluster.urls.detail, 302)
    messages.assert_message_contains(
        response,
        "The cluster can't be extended anymore since it's not active."
    )

    cluster.refresh_from_db()
    assert cluster.lifetime_extension_count == 0
    assert cluster.expires_at == original_expires_at
