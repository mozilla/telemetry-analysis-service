# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

from atmo.clusters import models, tasks


def test_deactivate_clusters(mocker, one_hour_ago, cluster_factory):
    cluster = cluster_factory(
        end_date=one_hour_ago,
        most_recent_status=models.Cluster.STATUS_WAITING,
    )
    deactivate = mocker.patch('atmo.clusters.models.Cluster.deactivate')
    result = tasks.deactivate_clusters()
    assert deactivate.call_count == 1
    assert result == [[cluster.identifier, cluster.pk]]


def test_dont_deactivate_clusters(mocker, one_hour_ahead, cluster_factory):
    cluster_factory(
        end_date=one_hour_ahead,
        most_recent_status=models.Cluster.STATUS_WAITING,
    )
    deactivate = mocker.patch('atmo.clusters.models.Cluster.deactivate')
    result = tasks.deactivate_clusters()
    assert deactivate.call_count == 0
    assert result == []


def test_send_expiration_mails(mocker, now, cluster):
    cluster.end_date = now + timedelta(minutes=59)  # 1 hours is the cut-off
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
        start_date=now - timedelta(days=1),
        most_recent_status=models.Cluster.STATUS_RUNNING,
    )
    cluster2 = cluster_factory(
        created_by=user,
        start_date=now - timedelta(days=2),
        most_recent_status=models.Cluster.STATUS_RUNNING,
    )
    cluster3 = cluster_factory(
        created_by=user,
        start_date=now - timedelta(days=3),
        most_recent_status=models.Cluster.STATUS_RUNNING,
    )
    cluster_provisioner_list = mocker.patch(
        'atmo.clusters.provisioners.ClusterProvisioner.list',
        return_value=[
            {
                'jobflow_id': cluster1.jobflow_id,
                'state': cluster1.most_recent_status,
                'start_time': cluster1.start_date,
                'state_change_reason_code': '',
                'state_change_reason_message': '',
            },
            {
                'jobflow_id': cluster2.jobflow_id,
                'state': cluster2.most_recent_status,
                'start_time': cluster2.start_date,
                'state_change_reason_code': '',
                'state_change_reason_message': '',
            },
            {
                'jobflow_id': cluster3.jobflow_id,
                'state': models.Cluster.STATUS_WAITING,
                'start_time': cluster3.start_date,
                'state_change_reason_code': '',
                'state_change_reason_message': '',
            },
            # the cluster that should be ignored
            {
                'jobflow_id': 'j-some-other-id',
                'state': models.Cluster.STATUS_RUNNING,
                'start_time': now - timedelta(days=10),
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
    # only one cluster status was updated
    assert cluster_save.call_count == 1
    assert result == [
        cluster3.identifier,
    ]
