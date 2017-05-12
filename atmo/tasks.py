# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from celery.utils.log import get_task_logger
from guardian.utils import clean_orphan_obj_perms

from ..celery import celery

logger = get_task_logger(__name__)


@celery.task
def cleanup_permissions():
    clean_orphan_obj_perms()
