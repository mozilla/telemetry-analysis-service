# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_ssh_public_key
from django import forms
from django.core.exceptions import ValidationError

from ..forms.mixins import AutoClassFormMixin, CreatedByModelFormMixin
from .models import SSHKey
from .utils import calculate_fingerprint


class SSHKeyForm(AutoClassFormMixin, CreatedByModelFormMixin):
    """
    The form to be used when uploaded new SSH keys.
    """
    prefix = 'sshkey'

    key_file = forms.FileField(
        label='Or select a .pub file from your computer',
        help_text='This can usually be found in <code>~/.ssh/</code> on your computer.',
        required=False,
        widget=forms.FileInput(attrs={'accept': '.pub'}),
    )

    def clean_key(self):
        """
        Checks if the submitted key data:

        - isn't larger than 100kb
        - is a valid SSH public key (e.g. dismissing if it's a private key)
        - does not match any of the :attr:`valid key data prefixes
          <~atmo.keys.models.SSHKey.VALID_PREFIXES>`
        - already exists in the database
        """
        key = self.cleaned_data['key'].strip()
        if len(key) > 100000:
            raise ValidationError(
                'The submitted key was larger than 100kB, '
                'please submit a smaller one'
            )

        try:
            load_ssh_public_key(key.encode('utf-8'), backend=default_backend())
        except ValueError:
            raise ValidationError(
                'The submitted key is invalid or misformatted.'
            )
        except UnsupportedAlgorithm:
            raise ValidationError(
                'The submitted key is not supported. It should start with '
                'one of the following prefixes: %s.' %
                ', '.join(SSHKey.VALID_PREFIXES)
            )
        fingerprint = calculate_fingerprint(key)
        if self.created_by.created_sshkeys.filter(fingerprint=fingerprint).exists():
            raise ValidationError(
                'There is already a SSH key with the fingerprint %s. '
                'Please try a different one or use the one already uploaded.' % fingerprint,
            )
        return key

    class Meta:
        model = SSHKey
        fields = ['title', 'key', 'key_file']
        widgets = {
            'key': forms.Textarea(
                attrs={
                    'placeholder': 'Drag and drop a key file with the ".pub" '
                                   'file extension here, paste the content '
                                   'manually or use the file selector below',
                }),
        }
