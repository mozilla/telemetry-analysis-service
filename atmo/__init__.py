# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import os

default_app_config = 'atmo.apps.AtmoAppConfig'


def get_revision():
    "Return the Git revision stored in revision.txt"
    base_dir = os.path.dirname(os.path.dirname(__file__))
    revision_txt_path = os.path.join(base_dir, 'revision.txt')
    if os.path.exists(revision_txt_path):
        with open(revision_txt_path, 'r') as revision_txt:
            return revision_txt.read().strip()
    return None
