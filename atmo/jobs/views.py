# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import logging

from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import (HttpResponse, HttpResponseNotFound,
                         StreamingHttpResponse)
from django.shortcuts import redirect, render, get_object_or_404
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import get_valid_filename

from ..clusters.models import EMRRelease
from ..decorators import (change_permission_required,
                          delete_permission_required, modified_date,
                          view_permission_required)
from .forms import EditSparkJobForm, NewSparkJobForm, SparkJobAvailableForm
from .models import SparkJob

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
    """
    View to schedule a new Spark job to run on AWS EMR.
    """
    initial = {
        'identifier': '',
        'size': 1,
        'interval_in_hours': SparkJob.INTERVAL_WEEKLY,
        'job_timeout': 24,
        'start_date': timezone.now(),
        'emr_release': EMRRelease.objects.stable().first(),
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
    """
    View to edit a scheduled Spark job that runs on AWS EMR.
    """
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
    """
    View to delete a scheduled Spark job and then redirects to the dashboard.
    """
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
@modified_date
def detail_spark_job(request, id):
    """
    View to show the details for the scheduled Spark job with the given ID.
    """
    spark_job = SparkJob.objects.get(pk=id)
    context = {
        'spark_job': spark_job,
    }
    if spark_job.latest_run:
        context['modified_date'] = spark_job.latest_run.modified_at
    return TemplateResponse(request, 'atmo/jobs/detail.html', context=context)


@login_required
@view_permission_required(SparkJob)
@modified_date
def detail_zeppelin_job(request, id):
    """
    View to show the details for the scheduled Zeppelin job with the given ID.
    """
    spark_job = get_object_or_404(SparkJob, pk=id)
    response = ''
    if spark_job.results:
        markdown_url = ''.join([x for x in spark_job.results['data'] if x.endswith('md')])
        bucket = settings.AWS_CONFIG['PUBLIC_DATA_BUCKET']
        markdown_file = spark_job.provisioner.s3.get_object(Bucket=bucket,
                                                            Key=markdown_url)
        response = markdown_file['Body'].read().decode('utf-8')

    context = {
        'markdown': response
    }
    return TemplateResponse(request, 'atmo/jobs/zeppelin_notebook.html', context=context)


@login_required
@view_permission_required(SparkJob)
def download_spark_job(request, id):
    """
    Download the notebook file for the scheduled Spark job with the given ID.
    """
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


@login_required
@view_permission_required(SparkJob)
def run_spark_job(request, id):
    """
    Run a scheduled Spark job right now, out of sync with its actual schedule.

    This will actively ask for confirmation to run the Spark job.
    """
    spark_job = SparkJob.objects.get(pk=id)
    if not spark_job.is_runnable:
        messages.error(
            request,
            mark_safe(
                '<h4>Run now unavailable.</h4>'
                "The Spark job can't be run manually at this time. Please try again later."
            )
        )
        return redirect(spark_job)

    if request.method == 'POST':
        if spark_job.latest_run:
            try:
                spark_job.latest_run.sync()
            except ClientError:
                messages.error(
                    request,
                    mark_safe(
                        '<h4>Spark job API error</h4>'
                        "The Spark job can't be run at the moment since there was a "
                        "problem with fetching the status of the previous job run. "
                        "Please try again later."
                    )
                )
                return redirect(spark_job)

        spark_job.run()
        latest_run = spark_job.get_latest_run()
        if latest_run:
            schedule_entry = spark_job.schedule.get()
            schedule_entry.reschedule(
                last_run_at=spark_job.latest_run.scheduled_at,
            )
        return redirect(spark_job)

    context = {
        'spark_job': spark_job,
    }
    return render(request, 'atmo/jobs/run.html', context=context)
