# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse

from . import models
from ..forms.mixins import AutoClassFormMixin, CreatedByModelFormMixin
from ..keys.models import SSHKey


class EMRReleaseChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        super().__init__(
            label='EMR release',
            queryset=models.EMRRelease.objects.all(),
            required=True,
            empty_label=None,
            widget=forms.RadioSelect(attrs={
                'required': 'required',
                'class': 'radioset',
            }),
            help_text=models.Cluster.EMR_RELEASE_HELP,
        )

    def label_from_instance(self, obj):
        label = obj.version
        extra = []
        if obj.is_experimental:
            extra.append('experimental')
        elif obj.is_deprecated:
            extra.append('deprecated')
        if extra:
            label = '%s (%s)' % (label, ', '.join(extra))
        return label


class NewClusterForm(AutoClassFormMixin, CreatedByModelFormMixin,
                     forms.ModelForm):
    prefix = 'new'

    identifier = forms.RegexField(
        required=True,
        label='Identifier',
        regex=r'^[a-z0-9-]{1,100}$',
        widget=forms.TextInput(attrs={
            'pattern': r'[a-z0-9-]{1,100}',
            'data-parsley-pattern-message': 'Identifier contains invalid characters.',
        }),
        help_text='A unique identifier for your cluster, visible in '
                  'the AWS management console. (Lowercase, use hyphens '
                  'instead of spaces.)'
    )
    size = forms.IntegerField(
        label='Size',
        required=True,
        min_value=1,
        max_value=settings.AWS_CONFIG['MAX_CLUSTER_SIZE'],
        widget=forms.NumberInput(attrs={
            'min': '1',
            'max': str(settings.AWS_CONFIG['MAX_CLUSTER_SIZE']),
        }),
        help_text=('Number of workers to use in the cluster, between 1 and %s. '
                   'For testing or development 1 is recommended.' %
                   settings.AWS_CONFIG['MAX_CLUSTER_SIZE'])
    )
    lifetime = forms.IntegerField(
        label='Lifetime',
        required=True,
        min_value=2,
        max_value=settings.AWS_CONFIG['MAX_CLUSTER_LIFETIME'],
        widget=forms.NumberInput(attrs={
            'min': '2',
            'max': str(settings.AWS_CONFIG['MAX_CLUSTER_LIFETIME']),
        }),
        help_text=('Lifetime in hours after which the cluster is automatically '
                   'terminated, between 2 and %s.' %
                   settings.AWS_CONFIG['MAX_CLUSTER_LIFETIME'])
    )
    ssh_key = forms.ModelChoiceField(
        label='SSH key',
        queryset=SSHKey.objects.all(),
        required=True,
        empty_label=None,
    )
    emr_release = EMRReleaseChoiceField()

    class Meta:
        model = models.Cluster
        fields = ['identifier', 'size', 'lifetime', 'ssh_key', 'emr_release']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
                    'class': 'radioset',
                },
            )


class ExtendClusterForm(AutoClassFormMixin, forms.Form):
    prefix = 'extend'
    extension = forms.IntegerField(
        label='Lifetime extension in hours',
        required=True,
        min_value=2,
        max_value=settings.AWS_CONFIG['MAX_CLUSTER_LIFETIME'],
        widget=forms.NumberInput(attrs={
            'min': '2',
            'max': str(settings.AWS_CONFIG['MAX_CLUSTER_LIFETIME']),
        }),
        help_text=("Number of hours to extend the cluster's lifetime with, between 2 and %s." %
                   settings.AWS_CONFIG['MAX_CLUSTER_LIFETIME'])
    )
