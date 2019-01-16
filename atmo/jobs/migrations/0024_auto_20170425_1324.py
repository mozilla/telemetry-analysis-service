# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-04-25 13:24
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [("jobs", "0023_sparkjob_expired_date")]

    operations = [
        migrations.AddField(
            model_name="sparkjob",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="sparkjob",
            name="modified_at",
            field=models.DateTimeField(
                auto_now=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
    ]
