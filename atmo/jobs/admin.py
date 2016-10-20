from django.contrib import admin

from .models import SparkJob


@admin.register(SparkJob)
class SparkJobAdmin(admin.ModelAdmin):
    pass
