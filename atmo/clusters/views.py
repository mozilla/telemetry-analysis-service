# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe

from .. import names
from ..decorators import (change_permission_required, delete_permission_required,
                          modified_date, view_permission_required)
from ..models import next_field_value
from .forms import ExtendClusterForm, NewClusterForm
from .models import Cluster, EMRRelease


@login_required
def new_cluster(request):
    identifier = names.random_scientist()
    next_identifier = next_field_value(Cluster, 'identifier', identifier)
    initial = {
        'identifier': next_identifier,
        'size': Cluster.DEFAULT_SIZE,
        'lifetime': Cluster.DEFAULT_LIFETIME,
        'emr_release': EMRRelease.objects.stable().first(),
    }
    ssh_key_count = request.user.created_sshkeys.count()

    if ssh_key_count == 0:
        messages.error(
            request,
            mark_safe(
                '<h4>No SSH keys associated to you.</h4>'
                'Please upload one below to be able to launch a cluster. '
                'This is a one-time step.'
            )
        )
        return redirect('keys-new')
    else:
        # If 1 or more ssh keys, make the last pre-selected.
        initial['ssh_key'] = request.user.created_sshkeys.last()

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
    return render(request, 'atmo/clusters/new.html', context)


@login_required
@delete_permission_required(Cluster)
def terminate_cluster(request, id):
    cluster = Cluster.objects.get(id=id)
    if not cluster.is_active:
        return redirect(cluster)

    if request.method == 'POST':
        cluster.deactivate()
        return redirect(cluster)

    context = {
        'cluster': cluster,
    }
    return render(request, 'atmo/clusters/terminate.html', context=context)


@login_required
@change_permission_required(Cluster)
def extend_cluster(request, id):
    cluster = Cluster.objects.get(id=id)
    if not cluster.is_active:
        messages.error(
            request,
            mark_safe(
                '<h4>Cluster not active.</h4>'
                "The cluster can't be extended anymore since it's not active."
            )
        )
        return redirect(cluster)
    initial = {
        'extension': Cluster.DEFAULT_LIFETIME
    }
    form = ExtendClusterForm(initial=initial)

    if request.method == 'POST':
        form = ExtendClusterForm(
            data=request.POST,
            initial=initial,
        )
        if form.is_valid():
            cluster.extend(form.cleaned_data['extension'])  # updates expires_at and saves the cluster
            return redirect(cluster)

    context = {
        'cluster': cluster,
        'form': form,
    }
    return render(request, 'atmo/clusters/extend.html', context=context)


@login_required
@view_permission_required(Cluster)
@modified_date
def detail_cluster(request, id):
    cluster = Cluster.objects.get(id=id)
    context = {
        'cluster': cluster,
        'modified_date': cluster.modified_at,
    }
    return TemplateResponse(request=request, template='atmo/clusters/detail.html', context=context)
