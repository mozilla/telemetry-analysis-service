# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse

from . import models
from ..forms.mixins import CreatedByModelFormMixin, AutoClassFormMixin
from ..keys.models import SSHKey


class NewClusterForm(AutoClassFormMixin, CreatedByModelFormMixin,
                     forms.ModelForm):
    prefix = 'new'

    identifier = forms.RegexField(
        required=True,
        label='Identifier',
        regex=r'^[a-z0-9-]{1,100}$',
        widget=forms.TextInput(attrs={
            'required': 'required',
            'pattern': r'[a-z0-9-]{1,100}',
            'data-parsley-pattern-message': 'Identifier contains invalid characters.',
        }),
        help_text='A unique identifier to identify your cluster, visible in '
                  'the AWS management console. (Lowercase, use hyphens '
                  'instead of spaces.)'
    )
    size = forms.IntegerField(
        label='Size',
        required=True,
        min_value=1,
        max_value=settings.AWS_CONFIG['MAX_CLUSTER_SIZE'],
        widget=forms.NumberInput(attrs={
            'required': 'required',
            'min': '1',
            'max': str(settings.AWS_CONFIG['MAX_CLUSTER_SIZE']),
        }),
        help_text='Number of workers to use in the cluster '
                  '(1 is recommended for testing or development).'
    )
    ssh_key = forms.ModelChoiceField(
        label='SSH key',
        queryset=SSHKey.objects.all(),
        required=True,
        empty_label=None,
        widget=forms.Select(attrs={
            'required': 'required',
        }),
    )

    class Meta:
        model = models.Cluster
        fields = ['identifier', 'size', 'ssh_key', 'emr_release']
        widgets = {
            'emr_release': forms.RadioSelect(attrs={
                'required': 'required',
                'class': 'radioset',
            }),
        }

    def __init__(self, *args, **kwargs):
        super(NewClusterForm, self).__init__(*args, **kwargs)
        user_sshkeys = self.created_by.created_sshkeys.all()
        self.fields['ssh_key'].queryset = user_sshkeys.all()
        self.fields['ssh_key'].help_text = (
            'The SSH key to deploy to the cluster. '
            'See <a href="%s">your keys</a> or '
            '<a href="%s">add a new one</a>.' %
            (reverse('keys-list'), reverse('keys-new'))
        )
        # if there are fewer options we just show radio select buttons
        if user_sshkeys.count() <= 6:
            self.fields['ssh_key'].widget = forms.RadioSelect(
                choices=self.fields['ssh_key'].choices,
                attrs={
                    'required': 'required',
                    'class': 'radioset',
                },
            )
