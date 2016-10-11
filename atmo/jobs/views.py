import logging
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, get_object_or_404, render

from session_csrf import anonymous_csrf

from .models import SparkJob
from . import forms


logger = logging.getLogger("django")


@login_required
@anonymous_csrf
@require_POST
def new_spark_job(request):
    form = forms.NewSparkJobForm(request.user, request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also magically create the job for us
    return redirect("/")


@login_required
@anonymous_csrf
@require_POST
def edit_spark_job(request):
    form = forms.EditSparkJobForm(request.user, request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also update the job for us
    return redirect("/")


@login_required
@anonymous_csrf
@require_POST
def delete_spark_job(request):
    form = forms.DeleteSparkJobForm(request.user, request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also delete the job for us
    return redirect("/")


@login_required
def detail_spark_job(request, id):
    job = get_object_or_404(SparkJob, created_by=request.user, pk=id)
    return render(request, 'atmo/detail-spark-job.html', context={'job': job})
