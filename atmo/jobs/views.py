# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
import logging
from django import forms
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.utils.text import get_valid_filename
from django.utils import timezone

from allauth.account.utils import user_display

from .forms import (NewSparkJobForm, EditSparkJobForm, DeleteSparkJobForm,
                    TakenSparkJobForm)
from .models import SparkJob
from ..models import next_field_value

logger = logging.getLogger("django")


@login_required
def check_identifier_taken(request):
    """
    Given a Spark job identifier checks if one already exists.
    """
    form = TakenSparkJobForm(request.GET)
    if form.is_valid():
        identifier = form.cleaned_data['identifier']
        queryset = SparkJob.objects.filter(identifier=identifier)
        instance_id = form.cleaned_data.get('id')
        if instance_id is not None:
            queryset = queryset.exclude(id=instance_id)
        if queryset.exists():
            response = {
                'error': 'Identifier is taken.',
                'identifier': identifier,
                'alternative': next_field_value(
                    SparkJob, 'identifier', identifier, queryset=queryset,
                ),
            }
        else:
            response = {
                'success': 'Identifier is available.',
                'identifier': identifier,
            }
    else:
        response = {'error': 'No identifier provided.'}
    return JsonResponse(response)


@login_required
def new_spark_job(request):
    identifier = u'{}-telemetry-scheduled-task'.format(user_display(request.user))
    next_identifier = next_field_value(SparkJob, 'identifier', identifier)
    initial = {
        'identifier': next_identifier,
        'size': 1,
        'interval_in_hours': SparkJob.INTERVAL_WEEKLY,
        'job_timeout': 24,
        'start_date': timezone.now(),
    }
    form = NewSparkJobForm(
        request.user,
        initial=initial,
    )
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
    return render(request, 'atmo/spark-job-new.html', context)


@login_required
def edit_spark_job(request, id):
    spark_job = get_object_or_404(SparkJob, created_by=request.user, pk=id)
    form = EditSparkJobForm(
        request.user,
        instance=spark_job,
    )
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
    return render(request, 'atmo/spark-job-edit.html', context)


@login_required
def delete_spark_job(request, id):
    job = get_object_or_404(SparkJob, created_by=request.user, pk=id)
    form = DeleteSparkJobForm(
        request.user,
        instance=job,
    )
    if request.method == 'POST':
        form = DeleteSparkJobForm(
            request.user,
            data=request.POST,
            instance=job,
        )
        if form.is_valid():
            job.delete()
            return redirect('dashboard')
    context = {
        'job': job,
        'form': form,
    }
    return render(request, 'atmo/spark-job-delete.html', context=context)


@login_required
def detail_spark_job(request, id):
    job = get_object_or_404(SparkJob, created_by=request.user, pk=id)
    delete_form = DeleteSparkJobForm(
        request.user,
        instance=job,
    )
    # hiding the confirmation input on the detail page
    delete_form.fields['confirmation'].widget = forms.HiddenInput()
    context = {
        'job': job,
        'delete_form': delete_form,
    }
    if 'render' in request.GET and job.notebook_s3_key:
        context['notebook_content'] = job.notebook_s3_object['Body'].read()
    return render(request, 'atmo/spark-job-detail.html', context=context)


@login_required
def download_spark_job(request, id):
    job = get_object_or_404(SparkJob, created_by=request.user, pk=id)
    if job.notebook_s3_object:
        response = StreamingHttpResponse(
            job.notebook_s3_object['Body'].read(),
            content_type='application/x-ipynb+json',
        )
        response['Content-Disposition'] = ('attachment; filename=%s' %
                                           get_valid_filename(job.notebook_name))
        response['Content-Length'] = job.notebook_s3_object['ContentLength']
        return response

    raise Http404
