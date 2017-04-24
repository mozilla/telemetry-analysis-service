# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from atmo.clusters.admin import deactivate as deactivate_action
from atmo.clusters.models import Cluster


def test_deactivate_action(mocker, cluster_factory):
    deactivate_method = mocker.patch('atmo.clusters.models.Cluster.deactivate')
    cluster_factory.create_batch(5)
    deactivate_action(None, None, Cluster.objects.all())
    assert deactivate_method.call_count == 5
