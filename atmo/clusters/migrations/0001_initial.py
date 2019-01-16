# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-07-27 15:50
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Cluster",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "identifier",
                    models.CharField(
                        help_text="Cluster name, used to non-uniqely identify individual clusters.",
                        max_length=100,
                    ),
                ),
                (
                    "size",
                    models.IntegerField(
                        help_text="Number of computers  used in the cluster."
                    ),
                ),
                (
                    "public_key",
                    models.CharField(
                        help_text="Public key that should be authorized for SSH access to the cluster.",
                        max_length=100000,
                    ),
                ),
                (
                    "start_date",
                    models.DateTimeField(
                        blank=True,
                        help_text="Date/time that the cluster was started, or null if it isn't started yet.",
                        null=True,
                    ),
                ),
                (
                    "end_date",
                    models.DateTimeField(
                        blank=True,
                        help_text="Date/time that the cluster will expire and automatically be deleted.",
                        null=True,
                    ),
                ),
                (
                    "jobflow_id",
                    models.CharField(
                        blank=True,
                        help_text="AWS cluster/jobflow ID for the cluster, used for cluster management.",
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "most_recent_status",
                    models.CharField(
                        default="UNKNOWN",
                        help_text="Most recently retrieved AWS status for the cluster.",
                        max_length=50,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        help_text="User that created the cluster instance.",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cluster_created_by",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        )
    ]
