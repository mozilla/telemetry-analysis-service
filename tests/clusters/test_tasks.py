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
        'atmo.clusters.models.Cluster.get_info',
        return_value={
            'public_dns': public_dns,
        }
    )
    result = tasks.update_master_address(cluster.pk)
    assert result == public_dns


def test_update_master_address_noop(cluster_factory, mocker):
    public_dns = 'example.com'
    cluster = cluster_factory(master_address=public_dns)
    mocker.patch(
        'atmo.clusters.models.Cluster.get_info',
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
        'atmo.clusters.models.Cluster.get_info',
        return_value={
            'public_dns': '',
        }
    )
    result = tasks.update_master_address(cluster.pk)
    assert result is None
