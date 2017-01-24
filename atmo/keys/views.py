# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.utils.safestring import mark_safe

from guardian.shortcuts import get_objects_for_user

from .models import SSHKey
from .forms import SSHKeyForm
from ..decorators import delete_permission_required, view_permission_required


@login_required
def list_keys(request):
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
    key = get_object_or_404(SSHKey, pk=id)
    last_key = key.created_by.created_sshkeys.count() == 1
    if last_key:
        messages.error(
            request,
            mark_safe(
                '<h4>Key not deleted!</h4> '
                'At least one SSH key needs to exist, please add '
                'another one before you delete this one.'
            )
        )
        return redirect('keys-list')
    elif request.method == 'POST':
        message = mark_safe(
            'SSH key <strong>%s</strong> successfully deleted.' % key
        )
        key.delete()
        messages.success(request, message)
        return redirect('keys-list')
    context = {
        'key': key,
    }
    return render(request, 'atmo/keys/delete.html', context=context)
