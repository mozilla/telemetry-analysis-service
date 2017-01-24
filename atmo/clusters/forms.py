# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse

from . import models
from ..forms.mixins import CreatedByModelFormMixin, FormControlFormMixin
from ..keys.models import SSHKey


class SSHKeyChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return u'%s [%s]' % (obj, obj.fingerprint)


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
    ssh_key = SSHKeyChoiceField(
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

    def __init__(self, *args, **kwargs):
        super(NewClusterForm, self).__init__(*args, **kwargs)
        self.fields['ssh_key'].queryset = self.created_by.created_sshkeys.all()
        self.fields['ssh_key'].help_text = (
            'Feel free to review <a href="%s">your SSH keys</a> or '
            '<a href="%s">add a new SSH key</a>.' %
            (reverse('keys-list'), reverse('keys-new'))
        )
