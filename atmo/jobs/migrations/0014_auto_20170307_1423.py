# -*- coding: utf-8 -*-
# Generated by Django 1.9.11 on 2017-03-07 14:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("jobs", "0013_sparkjobrunalert")]

    operations = [
        migrations.AlterField(
            model_name="sparkjob",
            name="emr_release",
            field=models.CharField(
                choices=[("5.2.1", "5.2.1"), ("5.0.0", "5.0.0")],
                default="5.2.1",
                help_text='Different AWS EMR versions have different versions of software like Hadoop, Spark, etc. See <a href="http://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-whatsnew.html">what\'s new</a> in each.',
                max_length=50,
                verbose_name="EMR release",
            ),
        )
    ]
