# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat


class PublicKeyFileField(forms.FileField):
    """
    Custom Django for file field that only accepts SSH public keys.

    The cleaned data is the public key as a string.
    """
    def clean(self, data, initial=None):
        uploaded_file = super(PublicKeyFileField, self).clean(data, initial)
        if uploaded_file.size > 100000:
            raise ValidationError(
                'File size must be at most 100kB, actual size is {}'.format(
                    filesizeformat(uploaded_file.size)
                )
            )
        contents = uploaded_file.read()
        if not contents.startswith('ssh-rsa AAAAB3'):
            raise ValidationError(
                'Invalid public key (a public key should start with \'ssh-rsa AAAAB3\')'
            )
        return contents


class CachedFileField(forms.FileField):
    """
    A custom FileField class for use in conjunction with CachedFileModelFormMixin
    that allows storing uploaded file in a cache for re-submission.

    That requires moving the "required" validation into the form's clean
    method instead of handling it on field level.
    """
    def __init__(self, *args, **kwargs):
        self.real_required = kwargs.pop('required', True)
        kwargs['required'] = False
        super(CachedFileField, self).__init__(*args, **kwargs)
