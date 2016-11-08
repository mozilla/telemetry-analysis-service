# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from allauth.account.utils import user_display

from .forms import NewClusterForm, TerminateClusterForm
from .models import Cluster
from ..decorators import permission_granted


@login_required
def new_cluster(request):
    initial = {
        'identifier': u'{}-telemetry-analysis'.format(user_display(request.user)),
        'size': 1,
    }
    form = NewClusterForm(
        request.user,
        initial=initial,
    )
    if request.method == 'POST':
        form = NewClusterForm(
            request.user,
            data=request.POST,
            files=request.FILES,
            initial=initial,
        )
        if form.is_valid():
            cluster = form.save()  # this will also magically spawn the cluster for us
            return redirect(cluster)
    context = {
        'form': form,
    }
    return render(request, 'atmo/cluster-new.html', context)


@login_required
@permission_granted('clusters.view_cluster', Cluster)
def terminate_cluster(request, id):
    cluster = Cluster.objects.get(id=id)
    if not cluster.is_active:
        return redirect(cluster)

    form = TerminateClusterForm(
        request.user,
        instance=cluster,
    )
    if request.method == 'POST':
        form = TerminateClusterForm(
            request.user,
            data=request.POST,
            instance=cluster,
        )
        if form.is_valid():
            cluster.deactivate()
            return redirect(cluster)
    context = {
        'cluster': cluster,
        'form': form,
    }
    return render(request, 'atmo/cluster-terminate.html', context=context)


@login_required
@permission_granted('clusters.view_cluster', Cluster)
def detail_cluster(request, id):
    cluster = Cluster.objects.get(id=id)
    terminate_form = TerminateClusterForm(
        request.user,
        instance=cluster,
    )
    # hiding the confirmation input on the detail page
    terminate_form.fields['confirmation'].widget = forms.HiddenInput()
    context = {
        'cluster': cluster,
        'terminate_form': terminate_form,
    }
    return render(request, 'atmo/cluster-detail.html', context=context)
