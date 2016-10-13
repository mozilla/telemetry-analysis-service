# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib.auth.decorators import login_required

from .forms import NewClusterForm, EditClusterForm, TerminateClusterForm
from .models import Cluster


@login_required
def new_cluster(request):
    username = request.user.email.split("@")[0]
    initial = {
        "identifier": "{}-telemetry-analysis".format(username),
        "size": 1,
    }
    if request.method == 'POST':
        form = NewClusterForm(
            request.user,
            data=request.POST,
            files=request.FILES,
            initial=initial,
            prefix='new',
        )
        if form.is_valid():
            cluster = form.save()  # this will also magically spawn the cluster for us
            return redirect(cluster)
    else:
        form = NewClusterForm(
            request.user,
            initial=initial,
            prefix='new',
        )
    context = {
        'form': form,
    }
    return render(request, 'atmo/cluster-new.html', context)


@login_required
def edit_cluster(request, id):
    cluster = get_object_or_404(Cluster, created_by=request.user, pk=id)
    if not cluster.is_active:
        return redirect(cluster)
    if request.method == 'POST':
        form = EditClusterForm(
            request.user,
            data=request.POST,
            files=request.FILES,
            instance=cluster,
            prefix='edit',
        )
        if form.is_valid():
            cluster = form.save()  # this will also magically spawn the cluster for us
            return redirect(cluster)
    else:
        form = EditClusterForm(
            request.user,
            instance=cluster,
            prefix='edit',
        )
    context = {
        'form': form,
    }
    return render(request, 'atmo/cluster-edit.html', context)


@login_required
def terminate_cluster(request, id):
    cluster = get_object_or_404(Cluster, created_by=request.user, pk=id)
    if not cluster.is_active:
        return redirect(cluster)
    if request.method == 'POST':
        form = TerminateClusterForm(
            request.user,
            prefix='terminate',
            data=request.POST,
            instance=cluster,
        )
        if form.is_valid():
            cluster.deactivate()
            return redirect(cluster)
    else:
        form = TerminateClusterForm(
            request.user,
            prefix='terminate',
            instance=cluster,
        )
    context = {
        'cluster': cluster,
        'form': form,
    }
    return render(request, 'atmo/cluster-terminate.html', context=context)


@login_required
def detail_cluster(request, id):
    cluster = get_object_or_404(Cluster, created_by=request.user, pk=id)
    terminate_form = TerminateClusterForm(
        request.user,
        prefix='terminate',
        instance=cluster,
    )
    # hiding the confirmation input on the detail page
    terminate_form.fields['confirmation'].widget = forms.HiddenInput()
    context = {
        'cluster': cluster,
        'terminate_form': terminate_form,
    }
    return render(request, 'atmo/cluster-detail.html', context=context)
