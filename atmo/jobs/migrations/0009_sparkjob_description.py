# -*- coding: utf-8 -*-
# Generated by Django 1.9.11 on 2017-01-13 23:58
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("jobs", "0008_assign_more_perms")]

    operations = [
        migrations.AddField(
            model_name="sparkjob",
            name="description",
            field=models.TextField(default="", help_text="Job description."),
        )
    ]
