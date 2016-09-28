from django.shortcuts import redirect, get_object_or_404, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest

from session_csrf import anonymous_csrf

from . import forms
from .models import Cluster


@login_required
@anonymous_csrf
@require_POST
def new_cluster(request):
    form = forms.NewClusterForm(request.user, request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also magically spawn the cluster for us
    return redirect("/")


@login_required
@anonymous_csrf
@require_POST
def edit_cluster(request):
    form = forms.EditClusterForm(request.user, request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also update the cluster for us
    return redirect("/")


@login_required
@anonymous_csrf
@require_POST
def delete_cluster(request):
    form = forms.DeleteClusterForm(request.user, request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also terminate the cluster for us
    return redirect("/")


@login_required
def detail_cluster(request, id):
    cluster = get_object_or_404(Cluster, created_by=request.user, pk=id)
    return render(request, 'atmo/detail-cluster.html', context={'cluster': cluster})
