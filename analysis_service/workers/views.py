from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest

from session_csrf import anonymous_csrf

from . import forms


@login_required
@anonymous_csrf
@require_POST
def new_worker(request):
    form = forms.NewWorkerForm(request.user, request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors.as_json(escape_html=True))
    form.save()  # this will also magically create the worker for us
    return redirect("/")
