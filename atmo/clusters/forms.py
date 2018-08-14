# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.
from django import forms
from django.conf import settings
from django.core import validators
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe

from . import models
from ..forms.mixins import AutoClassFormMixin, CreatedByModelFormMixin
from ..keys.models import SSHKey


class EMRReleaseChoiceField(forms.ModelChoiceField):
    """
    A :class:`~django.forms.ModelChoiceField` subclass that uses
    :class:`~atmo.clusters.models.EMRRelease` objects for the choices
    and automatically uses a "radioset" rendering -- a horizontal button
    group for easier selection.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(
            label='EMR release',
            queryset=models.EMRRelease.objects.active().natural_sort_by_version(),
            required=True,
            empty_label=None,
            widget=forms.RadioSelect(attrs={
                'required': 'required',
                'class': 'radioset',
            }),
            help_text=models.Cluster.EMR_RELEASE_HELP,
        )

    def label_from_instance(self, obj):
        """
        Append the status of the EMR release if it's
        experimental or deprecated.
        """
        label = obj.version
        extra = []
        if obj.is_experimental:
            extra.append('<span class="label label-info">experimental</span>')
        elif obj.is_deprecated:
            extra.append('<span class="label label-warning">deprecated</span>')
        if extra:
            label = mark_safe('%s %s' % (label, ''.join(extra)))
        return label


class NewClusterForm(AutoClassFormMixin, CreatedByModelFormMixin,
                     forms.ModelForm):
    """
    A form used for creating new clusters.
    """
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
        # we define the max_value below in __init__ for non-maintainers
        min_value=1,
        widget=forms.NumberInput(attrs={'min': '1'}),
        help_text=('Number of workers to use in the cluster, with a minimum of 1 '
                   'but NO MAXIMUM because you are a cluster maintainer. '
                   'Remember, with great power comes great...cost.')
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
        # if the user is not a cluster maintainer, reset the max
        # to the default so they can't create larger clusters
        if not self.created_by.has_perm('clusters.maintain_cluster'):
            max_size = settings.AWS_CONFIG['MAX_CLUSTER_SIZE']
            self.fields['size'].max_value = max_size
            self.fields['size'].validators.append(
                validators.MaxValueValidator(max_size)
            )
            self.fields['size'].widget.attrs['max'] = max_size
            self.fields['size'].help_text = (
                'Number of workers to use in the cluster, between 1 and %s. '
                'For testing or development 1 is recommended.' %
                max_size
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
