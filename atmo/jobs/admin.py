from django.contrib import admin

from .models import SparkJob


def run_now(modeladmin, request, queryset):
    for job in queryset:
        job.run()


@admin.register(SparkJob)
class SparkJobAdmin(admin.ModelAdmin):
    list_display = [
        'identifier',
        'size',
        'created_by',
        'start_date',
        'end_date',
        'last_run_date',
        'is_enabled',
        'most_recent_status',
    ]
    list_filter = [
        'most_recent_status',
        'size',
        'is_enabled',
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
