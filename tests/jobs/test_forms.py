# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from atmo.jobs.forms import NewSparkJobForm


BASE_DATA = {
    # Replace these `None` values with pytest fixtures.
    'new-notebook': None,
    'new-emr_release': None,

    'new-identifier': 'test-spark-job',
    'new-description': 'A description',
    'new-notebook-cache': 'some-random-hash',
    'new-result_visibility': 'private',
    'new-size': 5,
    'new-interval_in_hours': 24,
    'new-job_timeout': 12,
    'new-start_date': '2016-04-05 13:25:47',
}


def test_new_sparkjob_form(user, emr_release, notebook_maker):

    data = BASE_DATA.copy()
    data.update({
        'new-emr_release': emr_release.version,
    })
    file_data = {
        'new-notebook': notebook_maker()
    }
    form = NewSparkJobForm(user, data, file_data)
    assert form.is_valid(), form.errors


def test_new_sparkjob_form_bad_notebook_extension(user, emr_release,
                                                  notebook_maker):
    data = BASE_DATA.copy()
    data.update({
        'new-emr_release': emr_release.version,
    })
    file_data = {
        'new-notebook': notebook_maker(extension='foo')
    }
    form = NewSparkJobForm(user, data, file_data)

    assert not form.is_valid()
    assert 'notebook' in form.errors
