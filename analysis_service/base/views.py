import logging
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseRedirect

from session_csrf import anonymous_csrf

import kronos

from analysis_service.base import forms
from analysis_service.base import models
from analysis_service.base.util import email


logger = logging.getLogger("django")


@login_required
def dashboard(request):
    username = request.user.email.split("@")[0]
    return render(request, 'analysis_service/dashboard.jinja', context={
        "active_clusters": models.Cluster.objects.filter(created_by=request.user)
                                                 .order_by("start_date"),
        "new_cluster_form": forms.NewClusterForm(request.user, initial={
            "identifier": "{}-telemetry-analysis".format(username),
            "size": 1,
        }),
        "edit_cluster_form": forms.EditClusterForm(request.user),
        "delete_cluster_form": forms.DeleteClusterForm(request.user),

        "active_workers": models.Worker.objects.filter(created_by=request.user)
                                               .order_by("start_date"),
        "new_worker_form": forms.NewWorkerForm(request.user, initial={
            "identifier": "{}-telemetry-worker".format(username),
        }),

        "active_scheduled_spark": models.ScheduledSpark.objects.filter(created_by=request.user)
                                                               .order_by("start_date"),
        "new_scheduled_spark_form": forms.NewScheduledSparkForm(request.user, initial={
            "identifier": "{}-telemetry-scheduled-task".format(username),
            "size": 1,
            "interval_in_hours": 24 * 7,
            "job_timeout": 24,
            "start_date": datetime.now(),
        }),
        "edit_scheduled_spark_form": forms.EditScheduledSparkForm(request.user),
        "delete_scheduled_spark_form": forms.DeleteScheduledSparkForm(request.user),
    })


@anonymous_csrf
def login(request):
    if request.user.is_authenticated():
        return redirect(dashboard)
    return render(request, 'analysis_service/login.jinja')


@login_required
@anonymous_csrf
@require_POST
def new_cluster(request):
    form = forms.NewClusterForm(request.user, request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also magically spawn the cluster for us
    return HttpResponseRedirect("/")


@login_required
@anonymous_csrf
@require_POST
def edit_cluster(request):
    form = forms.EditClusterForm(request.user, request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also update the cluster for us
    return HttpResponseRedirect("/")


@login_required
@anonymous_csrf
@require_POST
def delete_cluster(request):
    form = forms.DeleteClusterForm(request.user, request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also delete the cluster for us
    return HttpResponseRedirect("/")


@login_required
@anonymous_csrf
@require_POST
def new_worker(request):
    form = forms.NewWorkerForm(request.user, request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also magically create the worker for us
    return HttpResponseRedirect("/")


@login_required
@anonymous_csrf
@require_POST
def new_scheduled_spark(request):
    form = forms.NewScheduledSparkForm(request.user, request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also magically create the job for us
    return HttpResponseRedirect("/")


@login_required
@anonymous_csrf
@require_POST
def edit_scheduled_spark(request):
    form = forms.EditScheduledSparkForm(request.user, request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also update the job for us
    return HttpResponseRedirect("/")


@login_required
@anonymous_csrf
@require_POST
def delete_scheduled_spark(request):
    form = forms.DeleteScheduledSparkForm(request.user, request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also delete the job for us
    return HttpResponseRedirect("/")


# this function is called every hour
@kronos.register('0 * * * *')
def periodic_task():
    now = datetime.now()

    # go through clusters to kill or warn about ones that are expiring
    for cluster in models.Cluster.objects.all():
        if cluster.end_date >= now:  # the cluster is expired
            cluster.delete()
        elif cluster.end_date >= now + timedelta(hours=1):  # the cluster will expire in an hour
            email.send_email(
                email_address = cluster.created_by.email,
                subject = "Cluster {} is expiring soon!".format(cluster.identifier),
                body = (
                    "Your cluster {} will be terminated in roughly one hour, around {}. "
                    "Please save all unsaved work before the machine is shut down.\n"
                    "\n"
                    "This is an automated message from the Telemetry Analysis service. "
                    "See https://analysis.telemetry.mozilla.org/ for more details."
                ).format(cluster.identifier, now + timedelta(hours=1))
            )

    # kill expired workers
    for worker in models.Worker.objects.all():
        if worker.end_date >= now:  # the worker is expired
            worker.delete()

    # launch scheduled jobs if necessary
    models.ScheduledSpark.step_all()
