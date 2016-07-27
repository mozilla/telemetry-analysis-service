import logging
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest

from session_csrf import anonymous_csrf

from . import forms


logger = logging.getLogger("django")


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
    form.save()  # this will also delete the cluster for us
    return redirect("/")
