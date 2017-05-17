# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from datetime import timedelta

import pytest
from django.utils import timezone

from atmo.clusters import models


@pytest.mark.parametrize(
    # first is a regular pytest param, all other are pytest-factoryboy params
    ','.join([
        'queryset_method',
        'emr_release__is_experimental',
        'emr_release__is_deprecated',
        'emr_release__is_active',
    ]), [
        ['stable', False, False, True],
        ['experimental', True, False, True],
        ['deprecated', False, True, True],
    ])
def test_emr_release_querysets(queryset_method,
                               emr_release__is_active,
                               emr_release__is_deprecated,
                               emr_release__is_experimental,
                               emr_release):
    assert getattr(models.EMRRelease.objects, queryset_method)().exists()


@pytest.mark.parametrize(
    # first is a regular pytest param, second is a pytest-factoryboy param
    'queryset_method,cluster__most_recent_status', [
        ['active', models.Cluster.STATUS_STARTING],
        ['active', models.Cluster.STATUS_BOOTSTRAPPING],
        ['active', models.Cluster.STATUS_RUNNING],
        ['active', models.Cluster.STATUS_WAITING],
        ['active', models.Cluster.STATUS_TERMINATING],
        ['terminated', models.Cluster.STATUS_TERMINATED],
        ['failed', models.Cluster.STATUS_TERMINATED_WITH_ERRORS],
    ])
def test_cluster_querysets(queryset_method,
                           cluster__most_recent_status,
                           cluster):
    assert getattr(models.Cluster.objects, queryset_method)().exists()


def test_is_expiring_soon(cluster):
    assert not cluster.is_expiring_soon
    # the cut-off is at 1 hour
    cluster.expires_at = timezone.now() + timedelta(minutes=59)
    cluster.save()
    assert cluster.is_expiring_soon


def test_extend(client, user, cluster_factory):
    cluster = cluster_factory(
        most_recent_status=models.Cluster.STATUS_WAITING,
        created_by=user,
    )

    assert cluster.lifetime_extension_count == 0
    # expires_at auto-set by save() by cluster.lifetime
    assert cluster.expires_at is not None
    original_expires_at = cluster.expires_at

    cluster.extend(hours=3)
    cluster.refresh_from_db()
    assert cluster.lifetime_extension_count == 1
    assert cluster.expires_at > original_expires_at
    assert cluster.expires_at == original_expires_at + timedelta(hours=3)
