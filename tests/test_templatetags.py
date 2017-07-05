# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from atmo.clusters.models import Cluster
from atmo.jobs.templatetags.notebook import is_notebook
from atmo.jobs.templatetags.status import status_color, status_icon
from atmo.templatetags import full_url, markdown, url_update


def test_is_notebook():
    assert is_notebook('test.ipynb')
    assert is_notebook('test.json')
    assert not is_notebook('test.txt')


def test_url_update():
    url = '/test/?foo=bar'

    assert url_update(url) == url
    assert url_update(url, fizz='buzz') == '/test/?foo=bar&fizz=buzz'


def test_get_full_url():
    assert full_url('/test/') == 'http://localhost:8000/test/'


def test_status_icon():
    for status in Cluster.ACTIVE_STATUS_LIST:
        assert status_icon(status) == 'glyphicon-play'
    for status in Cluster.TERMINATED_STATUS_LIST:
        assert status_icon(status) == 'glyphicon-stop'
    for status in Cluster.FAILED_STATUS_LIST:
        assert status_icon(status) == 'glyphicon-exclamation-sign'


def test_status_color():
    for status in Cluster.ACTIVE_STATUS_LIST:
        assert status_color(status) == 'status-running'
    for status in Cluster.TERMINATED_STATUS_LIST:
        assert status_color(status) is None
    for status in Cluster.FAILED_STATUS_LIST:
        assert status_color(status) == 'status-errors'


def test_markdown():
    assert markdown('**test**') == '<p><strong>test</strong></p>\n'
