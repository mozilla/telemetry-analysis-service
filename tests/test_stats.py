# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from atmo.stats.models import Metric


def test_metrics_record(now, one_hour_ago):
    Metric.record('metric-key-1')
    Metric.record('metric-key-2', 500)
    Metric.record('metric-key-3', data={'other-value': 'test'})
    Metric.record('metric-key-4', created_at=one_hour_ago,
                  data={'other-value-2': 100})

    m = Metric.objects.get(key='metric-key-1')
    assert m.value == 1
    assert m.created_at.replace(microsecond=0) == now
    assert m.data is None

    m = Metric.objects.get(key='metric-key-2')
    assert m.value == 500
    assert m.created_at.replace(microsecond=0) == now
    assert m.data is None

    m = Metric.objects.get(key='metric-key-3')
    assert m.value == 1
    assert m.created_at.replace(microsecond=0) == now
    assert m.data == {'other-value': 'test'}

    m = Metric.objects.get(key='metric-key-4')
    assert m.value == 1
    assert m.created_at.replace(microsecond=0) == one_hour_ago
    assert m.data == {'other-value-2': 100}
