# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from atmo.clusters.forms import EMRReleaseChoiceField


def test_emr_release_choice_field(emr_release_factory):
    regular = emr_release_factory()
    inactive = emr_release_factory(is_active=False)
    deprecated = emr_release_factory(is_deprecated=True)
    experimental = emr_release_factory(is_experimental=True)

    choice_field = EMRReleaseChoiceField()
    result = choice_field.widget.render('test', regular.pk)
    assert inactive.version not in result
    assert '%s</label>' % regular.version in result
    assert '%s (experimental)</label>' % experimental.version in result
    assert '%s (deprecated)</label>' % deprecated.version in result
