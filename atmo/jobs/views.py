# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotFound, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.text import get_valid_filename

from allauth.account.utils import user_display

from .forms import EditSparkJobForm, NewSparkJobForm, SparkJobAvailableForm
from .models import SparkJob
from ..decorators import (change_permission_required,
                          delete_permission_required, view_permission_required)
from ..models import next_field_value


logger = logging.getLogger("django")


@login_required
def check_identifier_available(request):
    """
    Given a Spark job identifier checks if one already exists.
    """
    form = SparkJobAvailableForm(request.GET)
    if form.is_valid():
        identifier = form.cleaned_data['identifier']
        if SparkJob.objects.filter(identifier=identifier).exists():
            response = HttpResponse('identifier unavailable')
        else:
            response = HttpResponseNotFound('identifier available')
    else:
        response = HttpResponseNotFound('identifier invalid')
    return response


@login_required
def new_spark_job(request):
    identifier = '{}-telemetry-scheduled-task'.format(user_display(request.user))
    next_identifier = next_field_value(SparkJob, 'identifier', identifier)
    initial = {
        'identifier': next_identifier,
        'size': 1,
        'interval_in_hours': SparkJob.INTERVAL_WEEKLY,
        'job_timeout': 24,
        'start_date': timezone.now(),
    }
    form = NewSparkJobForm(request.user, initial=initial)
    if request.method == 'POST':
        form = NewSparkJobForm(
            request.user,
            data=request.POST,
            files=request.FILES,
            initial=initial,
        )
        if form.is_valid():
            # this will also magically create the spark job for us
            spark_job = form.save()
            return redirect(spark_job)

    context = {
        'form': form,
    }
    return render(request, 'atmo/jobs/new.html', context)


@login_required
@change_permission_required(SparkJob)
def edit_spark_job(request, id):
    spark_job = SparkJob.objects.get(pk=id)
    form = EditSparkJobForm(request.user, instance=spark_job)
    if request.method == 'POST':
        form = EditSparkJobForm(
            request.user,
            data=request.POST,
            files=request.FILES,
            instance=spark_job,
        )
        if form.is_valid():
            # this will also update the job for us
            spark_job = form.save()
            return redirect(spark_job)
    context = {
        'form': form,
    }
    return render(request, 'atmo/jobs/edit.html', context)


@login_required
@delete_permission_required(SparkJob)
def delete_spark_job(request, id):
    spark_job = SparkJob.objects.get(pk=id)
    if request.method == 'POST':
        spark_job.delete()
        return redirect('dashboard')
    context = {
        'spark_job': spark_job,
    }
    return render(request, 'atmo/jobs/delete.html', context=context)


@login_required
@view_permission_required(SparkJob)
def detail_spark_job(request, id):
    spark_job = SparkJob.objects.get(pk=id)
    context = {
        'spark_job': spark_job,
    }
    if 'render' in request.GET:
        context['notebook_content'] = spark_job.notebook_s3_object['Body'].read().decode('utf-8')
    return render(request, 'atmo/jobs/detail.html', context=context)


@login_required
@view_permission_required(SparkJob)
def download_spark_job(request, id):
    spark_job = SparkJob.objects.get(pk=id)
    response = StreamingHttpResponse(
        spark_job.notebook_s3_object['Body'].read().decode('utf-8'),
        content_type='application/x-ipynb+json',
    )
    response['Content-Disposition'] = (
        'attachment; filename=%s' %
        get_valid_filename(spark_job.notebook_name)
    )
    response['Content-Length'] = spark_job.notebook_s3_object['ContentLength']
    return response
