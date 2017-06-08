# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from guardian.shortcuts import get_objects_for_user

from ..decorators import delete_permission_required, view_permission_required
from .forms import SSHKeyForm
from .models import SSHKey


@login_required
def list_keys(request):
    """View to list all SSH keys for the logged-in user."""
    ssh_keys = get_objects_for_user(
        request.user,
        'keys.view_sshkey',
        SSHKey.objects.all().order_by('-created_at'),
        use_groups=False,
        with_superuser=False,
    )
    context = {
        'ssh_keys': ssh_keys
    }
    return render(request, 'atmo/keys/list.html', context)


@login_required
def new_key(request):
    """View to upload a new SSH key for the logged-in user."""
    form = SSHKeyForm(request.user)
    if request.method == 'POST':
        form = SSHKeyForm(
            request.user,
            data=request.POST
        )
        if form.is_valid():
            key = form.save()
            messages.success(
                request,
                mark_safe('Key <strong>%s</strong> successfully added.' % key)
            )
            return redirect('keys-list')

    context = {
        'form': form,
    }
    return render(request, 'atmo/keys/new.html', context)


@login_required
@view_permission_required(SSHKey, ignore=['raw'])
def detail_key(request, id, raw=False):
    """
    View to show the details for the SSH key with the given ID.

    If the optional ``raw`` parameter is set it'll return the raw
    key data.
    """
    ssh_key = SSHKey.objects.get(pk=id)
    if raw:
        return HttpResponse(ssh_key.key, content_type='text/plain; charset=utf8')

    context = {
        'ssh_key': ssh_key,
    }
    return render(request, 'atmo/keys/detail.html', context=context)


@login_required
@delete_permission_required(SSHKey)
def delete_key(request, id):
    """View to delete an SSH key with the given ID."""
    ssh_key = get_object_or_404(SSHKey, pk=id)
    if request.method == 'POST':
        message = mark_safe(
            'SSH key <strong>%s</strong> successfully deleted.' % ssh_key
        )
        ssh_key.delete()
        messages.success(request, message)
        return redirect('keys-list')
    context = {
        'ssh_key': ssh_key,
    }
    return render(request, 'atmo/keys/delete.html', context=context)
