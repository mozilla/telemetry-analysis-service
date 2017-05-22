# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

from django.conf import settings

from atmo.clusters import models, tasks


def test_deactivate_clusters(mocker, one_hour_ago, cluster_factory):
    cluster = cluster_factory(
        expires_at=one_hour_ago,
        most_recent_status=models.Cluster.STATUS_WAITING,
    )
    deactivate = mocker.patch('atmo.clusters.models.Cluster.deactivate')
    result = tasks.deactivate_clusters()
    assert deactivate.call_count == 1
    assert result == [[cluster.identifier, cluster.pk]]


def test_dont_deactivate_clusters(mocker, one_hour_ahead, cluster_factory):
    cluster_factory(
        expires_at=one_hour_ahead,
        most_recent_status=models.Cluster.STATUS_WAITING,
    )
    deactivate = mocker.patch('atmo.clusters.models.Cluster.deactivate')
    result = tasks.deactivate_clusters()
    assert deactivate.call_count == 0
    assert result == []


def test_send_expiration_mails(mailoutbox, mocker, now, cluster_factory):
    cluster = cluster_factory(
        expires_at=now + timedelta(minutes=59),  # 1 hours is the cut-off
        most_recent_status=models.Cluster.STATUS_WAITING,
    )
    assert len(mailoutbox) == 0
    tasks.send_expiration_mails()
    assert len(mailoutbox) == 1
    message = mailoutbox[0]
    assert message.subject == (
        '%sCluster %s is expiring soon!' %
        (settings.EMAIL_SUBJECT_PREFIX, cluster.identifier)
    )
    assert message.from_email == settings.DEFAULT_FROM_EMAIL
    assert list(message.to) == [cluster.created_by.email]
    cluster.refresh_from_db()
    assert cluster.expiration_mail_sent


def test_update_master_address_success(cluster, mocker):
    public_dns = 'example.com'
    mocker.patch(
        'atmo.clusters.models.Cluster.info',
        new_callable=mocker.PropertyMock,
        return_value={
            'public_dns': public_dns,
        },
    )
    result = tasks.update_master_address(cluster.pk)
    assert result == public_dns


def test_update_master_address_noop(cluster_factory, mocker):
    public_dns = 'example.com'
    cluster = cluster_factory(master_address=public_dns)
    mocker.patch(
        'atmo.clusters.models.Cluster.info',
        new_callable=mocker.PropertyMock,
        return_value={
            'public_dns': public_dns,
        }
    )
    result = tasks.update_master_address(cluster.pk)
    assert result is None

    result = tasks.update_master_address(cluster.pk, force=True)
    assert result == public_dns


def test_update_master_address_empty(cluster, mocker):
    mocker.patch(
        'atmo.clusters.models.Cluster.info',
        new_callable=mocker.PropertyMock,
        return_value={
            'public_dns': '',
        }
    )
    result = tasks.update_master_address(cluster.pk)
    assert result is None


def test_update_clusters_empty():
    assert tasks.update_clusters() == []


def test_update_clusters(mocker, now, user, cluster_factory):
    cluster1 = cluster_factory(
        created_by=user,
        created_at=now - timedelta(days=1),
        most_recent_status=models.Cluster.STATUS_RUNNING,
    )
    cluster2 = cluster_factory(
        created_by=user,
        created_at=now - timedelta(days=2),
        most_recent_status=models.Cluster.STATUS_RUNNING,
    )
    cluster3 = cluster_factory(
        created_by=user,
        created_at=now - timedelta(days=3),
        most_recent_status=models.Cluster.STATUS_RUNNING,
    )
    cluster_provisioner_list = mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.list',
        return_value=[
            {
                'jobflow_id': cluster1.jobflow_id,
                'state': cluster1.most_recent_status,
                'creation_datetime': cluster1.created_at,
                'ready_datetime': None,
                'end_datetime': None,
                'state_change_reason_code': '',
                'state_change_reason_message': '',
            },
            {
                'jobflow_id': cluster2.jobflow_id,
                'state': cluster2.most_recent_status,
                'creation_datetime': cluster2.created_at,
                'ready_datetime': None,
                'end_datetime': None,
                'state_change_reason_code': '',
                'state_change_reason_message': '',
            },
            {
                'jobflow_id': cluster3.jobflow_id,
                'state': models.Cluster.STATUS_WAITING,
                'creation_datetime': cluster3.created_at,
                'ready_datetime': None,
                'end_datetime': None,
                'state_change_reason_code': '',
                'state_change_reason_message': '',
            },
            # the cluster that should be ignored
            {
                'jobflow_id': 'j-some-other-id',
                'state': models.Cluster.STATUS_RUNNING,
                'creation_datetime': now - timedelta(days=10),
                'ready_datetime': None,
                'end_datetime': None,
                'state_change_reason_code': '',
                'state_change_reason_message': '',
            },
        ]
    )
    cluster_save = mocker.patch(
        'atmo.clusters.models.Cluster.save',
    )
    result = tasks.update_clusters()
    cluster_provisioner_list.assert_called_once_with(
        created_after=(
            now - timedelta(days=3)
        ).replace(hour=0, minute=0, second=0)
    )
    assert cluster_save.call_count == 3
    assert result == [
        cluster1.identifier,
        cluster2.identifier,
        cluster3.identifier,
    ]
