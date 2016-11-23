# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms
from django.conf import settings

from . import models
from ..forms.mixins import CreatedByModelFormMixin, FormControlFormMixin
from ..forms.fields import PublicKeyFileField


class NewClusterForm(FormControlFormMixin, CreatedByModelFormMixin,
                     forms.ModelForm):
    prefix = 'new'

    identifier = forms.RegexField(
        label='Cluster identifier',
        required=True,
        regex=r'^[\w-]{1,100}$',
        widget=forms.TextInput(attrs={
            'required': 'required',
        }),
        help_text='A brief description of the cluster\'s purpose, '
                  'visible in the AWS management console.',
    )
    size = forms.IntegerField(
        label='Cluster size',
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
    public_key = PublicKeyFileField(
        label='Public SSH key',
        required=True,
        widget=forms.FileInput(attrs={
            'required': 'required',
        }),
        help_text='Upload your SSH <strong>public key</strong>, not private '
                  'key! This will generally be found in places like '
                  '<code>~/.ssh/id_rsa.pub</code>.'
    )

    class Meta:
        model = models.Cluster
        fields = ['identifier', 'size', 'public_key', 'emr_release']
