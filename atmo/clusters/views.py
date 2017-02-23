# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe

from allauth.account.utils import user_display

from .forms import NewClusterForm
from .models import Cluster
from ..decorators import view_permission_required, delete_permission_required


@login_required
def new_cluster(request):
    initial = {
        'identifier': '{}-telemetry-analysis'.format(user_display(request.user)),
        'size': 1,
    }
    ssh_key_count = request.user.created_sshkeys.count()

    if ssh_key_count == 0:
        messages.error(
            request,
            mark_safe(
                '<h4>No SSH keys associated to you.</h4>'
                'Please upload one below to be able to launch a cluster.'
                'This is one-time step.'
            )
        )
        return redirect('keys-new')
    elif ssh_key_count == 1:
        # If only 1 ssh key, make it pre-selected.
        initial['ssh_key'] = request.user.created_sshkeys.values('pk')[0]['pk']

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
@view_permission_required(Cluster)
def detail_cluster(request, id):
    cluster = Cluster.objects.get(id=id)
    context = {
        'cluster': cluster,
    }
    return render(request, 'atmo/clusters/detail.html', context=context)
