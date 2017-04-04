# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from atmo.jobs.templatetags.notebook import is_notebook
from atmo.templatetags import url_update, full_url


def test_is_notebook():
    assert is_notebook('test.ipynb')
    assert not is_notebook('test.txt')


def test_url_update():
    url = '/test/?foo=bar'

    assert url_update(url) == url
    assert url_update(url, fizz='buzz') == '/test/?foo=bar&fizz=buzz'


def test_get_full_url():
    assert full_url('/test/') == 'http://localhost:8000/test/'
