# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.contrib import admin
from .models import Cluster
from guardian.admin import GuardedModelAdmin


def terminate(modeladmin, request, queryset):
    for cluster in queryset:
        cluster.terminate()


@admin.register(Cluster)
class ClusterAdmin(GuardedModelAdmin):
    list_display = [
        'identifier',
        'size',
        'created_by',
        'start_date',
        'end_date',
        'jobflow_id',
        'emr_release',
        'most_recent_status',
    ]
    list_filter = [
        'most_recent_status',
        'size',
        'emr_release',
        'start_date',
        'end_date',
    ]
    search_fields = ['identifier', 'jobflow_id', 'created_by__email']
    actions = [terminate]
