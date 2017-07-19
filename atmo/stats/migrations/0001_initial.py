# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-19 21:23
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Metric',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(blank=True, db_index=True, default=django.utils.timezone.now, editable=False)),
                ('key', models.CharField(db_index=True, help_text='Name of the metric being recorded', max_length=100)),
                ('value', models.PositiveIntegerField(help_text='Integer value of the metric')),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, encoder=django.core.serializers.json.DjangoJSONEncoder, help_text='Extra data about this metric', null=True)),
            ],
        ),
    ]
