# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django.contrib import admin
from .models import SSHKey


@admin.register(SSHKey)
class SSHKeyAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'created_by',
        'fingerprint',
        'created_at',
        'modified_at',
    ]
    list_filter = [
        'created_at',
        'modified_at',
    ]
    search_fields = ['title', 'fingerprint', 'created_by__email', ]
