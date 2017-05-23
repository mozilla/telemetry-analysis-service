# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.contrib import admin
from guardian.admin import GuardedModelAdmin

from .models import SparkJob, SparkJobRun, SparkJobRunAlert


def run_now(modeladmin, request, queryset):
    for job in queryset:
        job.run()


class SparkJobRunInline(admin.TabularInline):
    model = SparkJobRun

    extra = 0
    fields = [
        'jobflow_id',
        'scheduled_at',
        'started_at',
        'ready_at',
        'status',
    ]
    readonly_fields = [
        'jobflow_id',
        'scheduled_at',
        'started_at',
        'ready_at',
        'status',
    ]


@admin.register(SparkJob)
class SparkJobAdmin(GuardedModelAdmin):
    actions = [run_now]
    inlines = [SparkJobRunInline]
    list_display = [
        'identifier',
        'size',
        'created_by',
        'start_date',
        'end_date',
        'is_enabled',
        'emr_release',
    ]
    list_filter = [
        'size',
        'is_enabled',
        'emr_release',
        'start_date',
        'end_date',
        'interval_in_hours',
        'runs__scheduled_at',
        'runs__status',
    ]
    search_fields = [
        'identifier',
        'description',
        'created_by__email',
        'runs__jobflow_id',
        'runs__status',
    ]


@admin.register(SparkJobRunAlert)
class SparkJobRunAlertAdmin(admin.ModelAdmin):
    list_display = [
        'run',
        'reason_code',
        'reason_message',
        'mail_sent_date',
    ]
    list_filter = [
        'reason_code',
        'mail_sent_date',
        'run__scheduled_at',
        'run__status',
    ]
    search_fields = [
        'reason_code',
        'reason_message',
    ]
