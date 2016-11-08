# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from .models import SparkJob


def run_now(modeladmin, request, queryset):
    for job in queryset:
        job.run()


@admin.register(SparkJob)
class SparkJobAdmin(GuardedModelAdmin):
    list_display = [
        'identifier',
        'size',
        'created_by',
        'start_date',
        'end_date',
        'last_run_date',
        'is_enabled',
        'emr_release',
        'most_recent_status',
    ]
    list_filter = [
        'most_recent_status',
        'size',
        'is_enabled',
        'emr_release',
        'start_date',
        'end_date',
        'last_run_date',
        'interval_in_hours',
    ]
    search_fields = [
        'identifier',
        'current_run_jobflow_id',
        'created_by__email',
        'most_recent_status',
    ]
    actions = [run_now]
